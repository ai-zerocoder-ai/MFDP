import logging
from pathlib import Path

import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from handlers.ui_helpers import swap_card
from handlers.keyboards import MenuCB, main_menu_kb, about_kb, back_only_kb
from config import BACKEND_URL

logger = logging.getLogger(__name__)

# Корневая директория проекта (две папки вверх от этого файла)
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"

WELCOME_IMAGE_PATH = ASSETS_DIR / "start.png"
ABOUT_IMAGE_PATH = ASSETS_DIR / "about.png"


class TattooGenStates(StatesGroup):
    GET_PROMPT = State()
    CONFIRM = State()


router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """
    Обработчик команды /start:
    1. Пытается зарегистрировать пользователя на backend.
    2. Отправляет приветственную карточку с изображением и кнопками главного меню.
    3. Сохраняет в state ID отправленного сообщения и путь к картинке welcome.
    """
    telegram_id = message.from_user.id

    # 1. Регистрация пользователя на backend (без фатального сбоя для бота)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{BACKEND_URL.rstrip('/')}/users/",
                json={"telegram_id": telegram_id},
            )
            if resp.status_code not in (200, 201, 204):
                # Логируем, если регистрация вернула неожиданный статус
                logger.warning(f"User registration returned status {resp.status_code}: {resp.text}")
    except httpx.HTTPError as e:
        logger.error(f"Registration error for telegram_id={telegram_id}: {e}")

    # 2. Отправка приветственной карточки с изображением
    caption = (
        "<b>Добро пожаловать в мир тату!</b>\n"
        "Выберите действие:"
    )

    try:
        photo_file = FSInputFile(WELCOME_IMAGE_PATH)
        sent = await message.answer_photo(photo=photo_file, caption=caption, reply_markup=main_menu_kb())
    except Exception as e:
        logger.error(f"Failed to send welcome image: {e}")
        sent = await message.answer(text=caption, reply_markup=main_menu_kb())

    # 3. Сохраняем ID сообщения и путь к изображению в state (для будущих переходов)
    await state.clear()
    await state.update_data(
        main_msg_id=sent.message_id,
        welcome_image=str(WELCOME_IMAGE_PATH)
    )


@router.callback_query(MenuCB.filter(F.action == "about"))
async def handle_about(call: CallbackQuery, state: FSMContext):
    """
    При выборе пункта "О проекте" заменяем текущее главное сообщение на карточку "О проекте".
    """
    caption = (
        "Tiny Tattoos - это MVP по созданию эскизов миниатюрных татуировок, выполненных в технике Single Line Art (одной линии).\n"
        "MVP разработан в рамках курса Практическая ML-инженерия от AI Talent Hub для представления на конкурсе проектов JMLC.\n"
        "Генерация осуществляется с использованием обученного на данный стиль LoRA для диффузионной генеративной модели семейства flux.\n\n"
        "В главном меню выберите «Сгенерировать эскиз».\n\n"
        "Один запрос на генерацию эскиза расходует 10 токенов."
    )

    try:
        await swap_card(
            origin=call,
            state=state,
            new_photo_path=str(ABOUT_IMAGE_PATH),
            new_caption=caption,
            new_kb=about_kb(),
        )
    except Exception as e:
        logger.error(f"Error showing About card: {e}")

    await call.answer()


@router.callback_query(MenuCB.filter(F.action == "balance"))
async def handle_balance(call: CallbackQuery, state: FSMContext):
    """
    При выборе пункта "Узнать баланс" запрашиваем баланс из backend
    и показываем пользователю.
    """
    await call.answer()  # Убираем «часики»
    telegram_id = call.from_user.id

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{BACKEND_URL.rstrip('/')}/users/?telegram_id={telegram_id}"
            )
        if resp.status_code == 200:
            users_list = resp.json()
            if isinstance(users_list, list) and users_list:
                tokens = users_list[0].get("tokens", 0)
            else:
                tokens = 0
        else:
            tokens = 0
            logger.warning(f"Balance request returned status {resp.status_code}: {resp.text}")
    except httpx.HTTPError as e:
        logger.error(f"Error fetching balance for {telegram_id}: {e}")
        tokens = 0

    # Формируем текст для показа баланса
    caption = f"💰 Баланс: <b>{tokens}</b> токенов"
    # Показываем карточку с балансом и кнопкой «В меню»
    try:
        await swap_card(
            origin=call,
            state=state,
            new_photo_path=None,
            new_caption=caption,
            new_kb=back_only_kb(),
        )
    except Exception as e:
        logger.error(f"Error showing balance card: {e}")



@router.callback_query(MenuCB.filter(F.action == "back"))
async def handle_back(call: CallbackQuery, state: FSMContext):
    """
    При выборе «Назад» (возврат в главное меню) заменяем текущее сообщение на главное меню.
    """
    data = await state.get_data()
    welcome_image = data.get("welcome_image", "")
    caption = "Выберите действие:"

    try:
        if welcome_image:
            await swap_card(
                origin=call,
                state=state,
                new_photo_path=welcome_image,
                new_caption=caption,
                new_kb=main_menu_kb(),
            )
        else:
            await swap_card(
                origin=call,
                state=state,
                new_photo_path=None,
                new_caption=caption,
                new_kb=main_menu_kb(),
            )
    except Exception as e:
        logger.error(f"Error returning to main menu: {e}")

    await call.answer()
