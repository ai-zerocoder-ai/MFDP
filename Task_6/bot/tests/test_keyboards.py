import pytest
from handlers.keyboards import main_menu_kb
from aiogram.types import InlineKeyboardMarkup


def extract_buttons(kb: InlineKeyboardMarkup):
    """
    Вспомогательная функция: из объекта InlineKeyboardMarkup
    возвращает простой список пар (text, callback_data) всех кнопок.
    """
    buttons = []
    for row in kb.inline_keyboard:  # каждая row — список InlineKeyboardButton
        for button in row:
            buttons.append((button.text, button.callback_data))
    return buttons


def test_main_menu_kb_structure():
    """
    Проверяем, что main_menu_kb() создаёт ровно три кнопки с правильными текстами и callback_data:
      1) "✨ Ознакомиться с проектом" → "menu:about"
      2) "Узнать баланс" (💳 или 💰) → "menu:balance"
      3) "🎨 Сгенерировать эскиз" → "menu:generate"
    """
    kb = main_menu_kb()
    assert isinstance(kb, InlineKeyboardMarkup)

    btns = extract_buttons(kb)
    # Должно быть ровно 3 кнопки
    assert len(btns) == 3

    # 1) «✨ Ознакомиться с проектом» → «menu:about»
    assert ("✨ Ознакомиться с проектом", "menu:about") in btns

    # 2) «Узнать баланс» → «menu:balance»
    #    Допускаем обе эмодзи-версии текста.
    balance_variants = {"💳 Узнать баланс", "💰 Узнать баланс"}
    assert any(text in balance_variants and callback == "menu:balance" for text, callback in btns)

    # 3) «🎨 Сгенерировать эскиз» → «menu:generate»
    assert ("✨ Сгенерировать эскиз", "menu:generate") in btns
