import logging
import os
import asyncio
import time
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
from celery_client import celery_app  # наш клиент Celery
from config import BACKEND_URL

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------
# ВАЖНО: этот путь должен совпадать с тем, куда воркер записывает PNG.
# В контейнере бота он видит bind-mount ../backend/temp_images как /app/backend/temp_images.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMP_DIR = BASE_DIR / "backend" / "temp_images"
# На случай, если папка ещё не создана (при сборке Dockerfile её могло не быть),
# убедимся, что она существует хотя бы пустая:
TEMP_DIR.mkdir(parents=True, exist_ok=True)
# --------------------------------------------------------------------

REQUEST_TIMEOUT = 30  # timeout для HTTP-запросов к бэкенду
MIN_TOKENS = 10       # минимальный баланс для одной генерации

router = Router()


@router.callback_query(MenuCB.filter(F.action == "generate"))
async def ask_prompt(call: CallbackQuery, state: FSMContext):
    """
    1) Просим пользователя ввести короткий английский prompt
    2) Сохраняем message_id инструкции, чтобы потом удалить
    3) Переходим в состояние GET_PROMPT
    """
    try:
        await call.answer()  # убираем «часики» на кнопке

        instruction_msg = await call.message.answer(
            "Введите описание тату 1–2 словами на английском (например: “Dragon”, “Rose”):"
        )
        await state.update_data(prompt_msg_id=instruction_msg.message_id)
        await state.set_state(TattooGenStates.GET_PROMPT)
    except Exception as e:
        logger.error(f"ask_prompt error: {e}", exc_info=True)
        await call.answer("⚠ Запрос не удался. Попробуйте снова.", show_alert=True)


@router.message(TattooGenStates.GET_PROMPT)
async def process_prompt(message: Message, state: FSMContext):
    """
    1) Удаляем сообщение-инструкцию и сообщение пользователя
    2) Валидируем prompt
    3) Сохраняем prompt в state
    4) Показываем кнопки «ДА!» / «НЕТ» (confirm_generation_kb)
    5) Переходим в состояние CONFIRM
    """
    data = await state.get_data()
    chat_id = message.chat.id
    prompt_text = message.text.strip()

    try:
        # 1. Удаляем сообщение-инструкцию (если сохранили ранее) и сам текст пользователя
        prompt_msg_id = data.get("prompt_msg_id")
        if prompt_msg_id:
            try:
                await message.bot.delete_message(chat_id, prompt_msg_id)
            except Exception as ex:
                logger.debug(f"Не удалось удалить сообщение-инструкцию: {ex}")

        try:
            await message.delete()
        except Exception as ex:
            logger.debug(f"Не удалось удалить сообщение пользователя: {ex}")

        # 2. Валидация prompt
        if not prompt_text:
            error_msg = await message.answer("⚠ Пожалуйста, введите запрос.")
            asyncio.create_task(_delete_after(error_msg, 10))
            return
        if len(prompt_text) > 20:
            error_msg = await message.answer("⚠ Слишком длинный запрос (максимум 20 символов).")
            asyncio.create_task(_delete_after(error_msg, 10))
            return

        # 3. Сохраняем prompt и убираем prompt_msg_id
        await state.update_data(description_en=prompt_text)
        await state.update_data(prompt_msg_id=None)

        # 4. Спрашиваем подтверждение генерации
        await swap_card(
            origin=message,
            state=state,
            new_photo_path=None,
            new_caption=f"✨ Генерируем эскиз «{prompt_text}»?",
            new_kb=confirm_generation_kb(),
        )
        # 5. Меняем состояние на CONFIRM
        await state.set_state(TattooGenStates.CONFIRM)

    except Exception as e:
        logger.error(f"process_prompt error: {e}", exc_info=True)
        error_msg = await message.answer("⚠ Ошибка при обработке вашего промпта. Попробуйте ещё раз.")
        asyncio.create_task(_delete_after(error_msg, 10))


@router.callback_query(MenuCB.filter(F.action == "confirm_gen"), TattooGenStates.CONFIRM)
async def confirm_generation(call: CallbackQuery, state: FSMContext):
    """
    1) Проверяем, что prompt в state существует.
    2) Проверяем баланс пользователя через HTTP GET к BACKEND_URL/users/
    3) Если недостаточно токенов — показываем предупреждение и возвращаем главное меню.
    4) Если токенов достаточно — отправляем задачу в Celery и начинаем опрос папки temp_images.
    5) Ждём до 30 секунд появления файла single_line_<telegram_id>_*.png в TEMP_DIR.
    6) Как только находим, отрисовываем swap_card с картинкой.
    7) Если за 30 секунд не нашли — показываем сообщение об ошибке таймаута.
    """

    data = await state.get_data()
    prompt_text = data.get("description_en", "").strip()

    if not prompt_text:
        await call.answer("⚠ Запрос не найден. Повторите попытку.", show_alert=True)
        return

    try:
        await call.answer("⏳ Проверяю баланс…")
        telegram_id = call.from_user.id

        # 1) Запрашиваем баланс у бэкенда
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(
                f"{BACKEND_URL.rstrip('/')}/users/?telegram_id={telegram_id}"
            )
        if resp.status_code == 200:
            users_list = resp.json()
            tokens = (
                users_list[0].get("tokens", 0)
                if isinstance(users_list, list) and users_list
                else 0
            )
        else:
            tokens = 0
            logger.warning(f"Balance request returned status {resp.status_code}: {resp.text}")

        # 2) Если токенов меньше MIN_TOKENS — предупреждаем и возвращаем в меню
        if tokens < MIN_TOKENS:
            warning_msg = await call.message.answer(
                "❗ Недостаточно токенов для генерации."
            )
            # Даём секунду, чтобы пользователь увидел предупреждение
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
                new_caption="👇 Выберите действие:",
                new_kb=main_menu_kb(),
            )
            await state.update_data(description_en=None)
            return

        # 3) У нас достаточно токенов → запускаем Celery-задачу.
        #    Заметьте: мы больше не ждём celery_result.get(). Просто запускаем задачу.
        celery_app.send_task(
            "apps.generations.tasks.generate_single_line_task",
            args=(telegram_id, prompt_text),
        )

        # 4) Извлекаем текущее время, чтобы отличать «новые» файлы
        start_time = time.time()

        # 5) Запускаем цикл ожидания: до 30 секунд
        found_path = None
        timeout_seconds = 30
        poll_interval = 1.0  # секунда между проверками

        while time.time() - start_time < timeout_seconds:
            # Собираем все файлы, подходящие под шаблон single_line_<id>_*.png
            pattern = f"single_line_{telegram_id}_*.png"
            candidates = list(TEMP_DIR.glob(pattern))
            if candidates:
                # Из кандидатов берём самый новый (по модификации или по имени)
                # Для надёжности проверим по времени: только файлы,
                # созданные после запуска (start_time), иначе старые «зашумы» могут попасть.
                new_candidates = [
                    p for p in candidates if p.stat().st_mtime >= start_time
                ]
                if new_candidates:
                    # Берём файл с наибольшим st_mtime
                    found_path = max(new_candidates, key=lambda p: p.stat().st_mtime)
                    break

            # Если пока не появился — ждём чуть-чуть и проверяем снова
            await asyncio.sleep(poll_interval)

        # 6) Если найти файл не удалось — таймаут
        if not found_path:
            timeout_msg = await call.message.answer(
                "❌ Не удалось сгенерировать изображение вовремя. Попробуйте снова."
            )
            asyncio.create_task(_delete_after(timeout_msg, 10))
            await state.update_data(description_en=None)
            return

        # 7) Вроде бы нашли свежий PNG: отрисовываем swap_card с картинкой + кнопка «В меню»
        await swap_card(
            origin=call,
            state=state,
            new_photo_path=str(found_path),
            new_caption=f"✨ Эскиз — «{prompt_text}».\n\nСохраните эскиз на устройство!",
            new_kb=back_only_kb(),
        )

        # 8) Запускаем отправку на backend в фоне (чтобы списать токены и сохранить запись)
        asyncio.create_task(
            _save_generation_in_background(
                image_path=str(found_path),
                prompt=prompt_text,
                user_id=telegram_id,
            )
        )

        # 9) Очищаем prompt из state
        await state.update_data(description_en=None)

    except Exception as e:
        logger.error(f"confirm_generation error: {e}", exc_info=True)
        error_msg = await call.message.answer("⚠ Произошла ошибка во время генерации. Попробуйте позже.")
        asyncio.create_task(_delete_after(error_msg, 10))


async def _save_generation_in_background(image_path: str, prompt: str, user_id: int):
    """
    Асинхронно отправляем сгенерированное изображение на backend,
    чтобы списать токены и сохранить запись.
    После этого удаляем локальный файл (чтобы temp_images не разрастался).
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
                        "charge_user": "true",
                    },
                )
                if resp.status_code not in (200, 201, 204):
                    logger.warning(
                        f"Failed to save generation on backend (status {resp.status_code}): {resp.text}"
                    )
    except Exception as e:
        logger.error(f"_save_generation_in_background error: {e}", exc_info=True)
    finally:
        # Удаляем локальный файл, даже если что-то пошло не так
        try:
            os.remove(image_path)
        except Exception:
            pass


@router.callback_query(MenuCB.filter(F.action == "cancel_gen"), TattooGenStates.CONFIRM)
async def cancel_generation(call: CallbackQuery, state: FSMContext):
    """
    Пользователь нажал «НЕТ» при подтверждении генерации:
    1) Возвращаем главное меню с welcome_image.
    2) Очищаем prompt (оставляем welcome_image и main_msg_id).
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
        await state.update_data(description_en=None)
        await state.update_data(prompt_msg_id=None)


async def _delete_after(msg: Message, delay_seconds: int):
    """
    Ждём delay_seconds секунд, а потом пытаемся удалить переданное сообщение.
    """
    await asyncio.sleep(delay_seconds)
    try:
        await msg.delete()
    except Exception:
        pass
