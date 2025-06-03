"""
Пакет `styles` содержит все «стили» (наборы правил и алгоритмов) для генерации
эскизов. Каждый файл-модуль в этом пакете должен реализовывать класс, наследующий
от `TattooStyle` (определённого в `styles/base.py`), и называться по схеме:
    `<имя_стиля>.py`.

По умолчанию функция `get_style(style_name)` возвращает экземпляр класса стиля
по его «текстовому ключу» (имени модуля без `.py`). Например:
    get_style("single_line_tattoo") → экземпляр `SingleLineTattooStyle`.
"""

import importlib
from typing import Any

from styles.base import TattooStyle


def get_style(style_name: str) -> TattooStyle:
    """
    Динамически импортирует модуль `styles.<style_name>` и создаёт экземпляр
    первого найденного внутри него класса-наследника TattooStyle (кроме самого
    абстрактного базового класса).

    Параметры:
      - style_name: строка (например, "single_line_tattoo"), соответствующая имени
        файла-модуля в папке styles (без расширения .py).

    Возвращает:
      - Экземпляр класса, унаследованного от TattooStyle.

    Исключения:
      - ValueError, если модуль не найден или внутри него нет корректного класса.
    """
    try:
        module = importlib.import_module(f"styles.{style_name}")
    except ImportError as e:
        raise ValueError(f"Не удалось найти стиль '{style_name}': {e}")

    # Ищем в модуле любой класс, наследующий TattooStyle (кроме самого TattooStyle)
    for attribute_name in dir(module):
        attribute = getattr(module, attribute_name)
        if (
            isinstance(attribute, type)
            and issubclass(attribute, TattooStyle)
            and attribute is not TattooStyle
        ):
            try:
                return attribute()  # создаём экземпляр
            except Exception as instantiation_error:
                raise ValueError(
                    f"Ошибка при создании экземпляра стиля '{attribute_name}': {instantiation_error}"
                )

    raise ValueError(f"В модуле styles.{style_name} не найден класс-наследник TattooStyle")
