from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class MenuCB(CallbackData, prefix="menu"):
    """
    CallbackData для основных действий меню бота.
    Поле `action` отвечает за тип нажатия, например:
      - "about"       — показать информацию о проекте,
      - "generate"    — начать процесс генерации эскиза,
      - "balance"     — узнать баланс,
      - "back"        — вернуться в главное меню,
      - "confirm_gen" — подтвердить генерацию,
      - "cancel_gen"  — отменить генерацию.
    """
    action: str


def main_menu_kb() -> InlineKeyboardMarkup:
    """
    Возвращает клавиатуру главного меню:
      1) «О проекте»
      2) «Сгенерировать эскиз»
      3) «Узнать баланс»
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="✨ Ознакомиться с проектом",
                callback_data=MenuCB(action="about").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="✨ Сгенерировать эскиз",
                callback_data=MenuCB(action="generate").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="💰 Узнать баланс",
                callback_data=MenuCB(action="balance").pack()
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def about_kb() -> InlineKeyboardMarkup:
    """
    Возвращает клавиатуру для раздела «О проекте» с одной кнопкой «Назад».
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data=MenuCB(action="back").pack()
                )
            ]
        ]
    )


def back_only_kb() -> InlineKeyboardMarkup:
    """
    Возвращает клавиатуру с одной кнопкой «В меню»,
    которая в обработчике переводит пользователя обратно в главное меню.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="В меню",
                    callback_data=MenuCB(action="back").pack()
                )
            ]
        ]
    )


def confirm_generation_kb() -> InlineKeyboardMarkup:
    """
    Возвращает клавиатуру для подтверждения генерации:
      • «✨ ДА!»   → MenuCB(action="confirm_gen")
      • «НЕТ»     → MenuCB(action="cancel_gen")
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✨ ДА!",
                    callback_data=MenuCB(action="confirm_gen").pack()
                ),
                InlineKeyboardButton(
                    text="НЕТ",
                    callback_data=MenuCB(action="cancel_gen").pack()
                )
            ]
        ]
    )
