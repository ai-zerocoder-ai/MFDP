import logging
import os
import asyncio
from pathlib import Path
from typing import List, Dict, Any

import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from handlers.ui_helpers import swap_card
from handlers.keyboards import (
    MenuCB,
    confirm_generation_kb,
    back_only_kb,
    main_menu_kb
)
from handlers.common_states import TattooGenStates
from celery_client import celery_app  # наш настроенный Celery‐клиент
from config import BACKEND_URL

logger = logging.getLogger(__name__)

# абсолютный путь для временных изображений (по аналогии с воркером)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMP_DIR = BASE_DIR / "backend" / "temp_images"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_TIMEOUT = 30
MIN_TOKENS = 10

router = Router()


@router.callback_query(MenuCB.filter(F.action == "generate"))
async def ask_prompt(call: CallbackQuery, state: FSMContext):
    """
    1) Отправляем пользователю инструкцию «Введите короткий prompt...»
       и сохраняем ID этого сообщения в state (чтобы потом удалить).
    2) Переходим в состояние GET_PROMPT.
    """
    try:
        await call.answer()  # убираем «часики»

        instruction_msg = await call.message.answer(
            "Введите описание тату 1–2 словами на английском (например: “Dragon”, “Rose”):"
        )
        # Сохраняем ID инструкции, чтобы потом её удалить
        await state.update_data(prompt_msg_id=instruction_msg.message_id)

        await state.set_state(TattooGenStates.GET_PROMPT)
    except Exception as e:
        logger.error(f"ask_prompt error: {e}", exc_info=True)
        await call.answer("⚠ Запрос не удался. Попробуйте снова.", show_alert=True)


@router.message(TattooGenStates.GET_PROMPT)
async def process_prompt(message: Message, state: FSMContext):
    """
    1) Удаляем из чата сообщение-инструкцию и сам текст пользователя.
    2) Сохраняем prompt в state и показываем кнопку подтверждения.
    3) Переходим в состояние CONFIRM.
    """
    data = await state.get_data()
    chat_id = message.chat.id
    prompt_text = message.text.strip()

    try:
        # 1. Удаляем инструкцию (если она есть)
        prompt_msg_id = data.get("prompt_msg_id")
        if prompt_msg_id:
            try:
                await message.bot.delete_message(chat_id, prompt_msg_id)
            except Exception as ex:
                logger.debug(f"Не удалось удалить сообщение-инструкцию: {ex}")

        # Удаляем сам месседж пользователя, который ввёл prompt
        try:
            await message.delete()
        except Exception as ex:
            logger.debug(f"Не удалось удалить пользовательский prompt: {ex}")

        # 2. Валидация prompt
        if not prompt_text:
            await message.answer("⚠ Пожалуйста, введите запрос.")
            return
        if len(prompt_text) > 10:
            await message.answer("⚠ Слишком длинный запрос (максимум 10 символов).")
            return

        # Сохраняем prompt в state для генерации
        await state.update_data(description_en=prompt_text)
        # Удаляем ключ prompt_msg_id, чтобы больше не мешал
        await state.update_data(prompt_msg_id=None)

        # 3. Спрашиваем подтверждение генерации (кнопки «ДА!» / «НЕТ»)
        await swap_card(
            origin=message,
            state=state,
            new_photo_path=None,
            new_caption=f"✨ Генерируем эскиз «{prompt_text}»?",
            new_kb=confirm_generation_kb(),
        )
        await state.set_state(TattooGenStates.CONFIRM)

    except Exception as e:
        logger.error(f"process_prompt error: {e}", exc_info=True)
        await message.answer("⚠ Ошибка при обработке вашего промпта. Попробуйте ещё раз.")


@router.callback_query(MenuCB.filter(F.action == "confirm_gen"), TattooGenStates.CONFIRM)
async def confirm_generation(call: CallbackQuery, state: FSMContext):
    """
    1) Проверяем, что prompt сохранился.
    2) Проверяем баланс.
    3) Если токенов достаточно — отправляем задачу в очередь.
    4) Ждём результат через celery_app.get(timeout).
    5) Выводим либо ошибку таймаута, либо сгенерированный эскиз.
    """
    data = await state.get_data()
    prompt_text = data.get("description_en", "").strip()

    if not prompt_text:
        await call.answer("⚠ Запрос не найден. Повторите попытку.", show_alert=True)
        return

    try:
        await call.answer("⏳ Проверяю баланс…")
        telegram_id = call.from_user.id

        # 1. Запрос баланса
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(
                f"{BACKEND_URL.rstrip('/')}/users/?telegram_id={telegram_id}"
            )
        if resp.status_code == 200:
            users_list = resp.json()
            tokens = users_list[0].get("tokens", 0) if isinstance(users_list, list) and users_list else 0
        else:
            tokens = 0
            logger.warning(f"Balance request returned status {resp.status_code}: {resp.text}")

        # 2. Если недостаточно токенов — выводим предупреждение и возвращаем меню
        if tokens < MIN_TOKENS:
            warning_msg = await call.message.answer(
                "❗ Недостаточно токенов для генерации."
            )
            # Ждём секунду, чтобы пользователь успел увидеть
            await asyncio.sleep(1.0)
            try:
                await warning_msg.delete()
            except Exception:
                pass

            common = await state.get_data()
            await swap_card(
                origin=call,
                state=state,
                new_photo_path=common.get("welcome_image", ""),
                new_caption="Выберите действие:",
                new_kb=main_menu_kb(),
            )
            await state.update_data(description_en=None)
            return

        # 3. Отправляем задачу в Celery и сразу ожидаем её выполнения (до 30 секунд)
        #    Используем send_task с полным именем, зарегистрированным воркером
        celery_result = celery_app.send_task(
            "apps.generations.tasks.generate_single_line_task",
            args=(telegram_id, prompt_text),
        )

        try:
            # Ждём максимум 30 секунд, чтобы воркер успел завершить generate_single_line_task
            result_list: List[str] = celery_result.get(timeout=30) or []
        except Exception as e:
            logger.error(f"Ошибка при получении результата задачи: {e}", exc_info=True)
            await call.message.answer(
                "❌ Не удалось сгенерировать изображение вовремя. Попробуйте снова."
            )
            await state.update_data(description_en=None)
            return

        # 4. Проверяем, вернулся ли непустой список с путями к PNG
        png_paths = [p for p in result_list if os.path.exists(p)]
        if not png_paths:
            await call.message.answer(
                "⚠ Произошла ошибка при генерации. Попробуйте позже."
            )
            await state.update_data(description_en=None)
            return

        generated_path = png_paths[0]
        # 5. Выводим пользователю картинку и кнопку «В меню»
        await swap_card(
            origin=call,
            state=state,
            new_photo_path=generated_path,
            new_caption=f"✨ Эскиз — «{prompt_text}».\n\nСохраните эскиз на устройство!",
            new_kb=back_only_kb(),
        )

        # 6. Фоновая отправка сгенерированной картинки на backend
        asyncio.create_task(_save_generation_in_background(
            image_path=generated_path,
            prompt=prompt_text,
            user_id=telegram_id
        ))

        await state.update_data(description_en=None)

    except Exception as e:
        logger.error(f"confirm_generation error: {e}", exc_info=True)
        await call.message.answer("⚠ Произошла ошибка во время генерации. Попробуйте позже.")


async def _save_generation_in_background(image_path: str, prompt: str, user_id: int):
    """
    Асинхронно отправляем сгенерированное изображение на backend.
    """
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            with open(image_path, "rb") as image_file:
                resp = await client.post(
                    f"{BACKEND_URL.rstrip('/')}/generations/",
                    files={"image": image_file},
                    data={
                        "prompt_en": prompt,
                        "telegram_id": str(user_id),
                        "charge_user": "true"
                    }
                )
                if resp.status_code not in (200, 201, 204):
                    logger.warning(
                        f"Failed to save generation on backend (status {resp.status_code}): {resp.text}"
                    )
    except Exception as e:
        logger.error(f"_save_generation_in_background error: {e}", exc_info=True)
    finally:
        try:
            os.remove(image_path)
        except Exception:
            pass

@router.callback_query(MenuCB.filter(F.action == "cancel_gen"), TattooGenStates.CONFIRM)
async def cancel_generation(call: CallbackQuery, state: FSMContext):
    """
    Если пользователь нажал «НЕТ» при подтверждении генерации:
    1) Возвращаем главное меню.
    2) Очищаем из state только prompt (оставляем main_msg_id и welcome_image).
    """
    try:
        await call.answer("⚠ Генерация отменена", show_alert=False)
        data = await state.get_data()
        await swap_card(
            origin=call,
            state=state,
            new_photo_path=data.get("welcome_image", ""),
            new_caption="👇 Выберите действие:",
            new_kb=main_menu_kb(),
        )
    except Exception as e:
        logger.error(f"cancel_generation error: {e}", exc_info=True)
        await call.answer("⚠ Не удалось отменить генерацию.", show_alert=True)
    finally:
        # Удаляем только prompt, не трогаем welcome_image и main_msg_id
        await state.update_data(description_en=None)
        await state.update_data(prompt_msg_id=None)
