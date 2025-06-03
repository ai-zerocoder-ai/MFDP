import asyncio
import logging
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import TELEGRAM_BOT_TOKEN
from handlers.start import router as start_router
from handlers.generation import router as generation_router

logger = logging.getLogger(__name__)


def setup_logging():
    """
    Настраивает логирование:
      - RotatingFileHandler: хранит до 5 файлов по 10 МБ каждый.
      - StreamHandler: выводит в консоль.
      - Уровень логирования — INFO (можно переключить через конфиг).
    """
    log_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Файловый хендлер с ротацией
    file_handler = RotatingFileHandler(
        filename="bot.log",
        mode="a",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)

    # Консольный хендлер
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)

    # Устанавливаем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


async def main():
    setup_logging()
    logger.info("Запуск бота...")

    # Инициализируем бота с HTML-парсингом по умолчанию
    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )

    # Хранилище состояний (в памяти); в продакшене можно заменить на RedisStorage
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрируем маршруты
    dp.include_router(start_router)
    dp.include_router(generation_router)

    try:
        # Запускаем polling
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"Ошибка в процессе polling: {e}")
    finally:
        # Корректно закрываем сессии и хранилище
        await bot.session.close()
        await storage.close()
        logger.info("Бот завершил работу.")


if __name__ == "__main__":
    asyncio.run(main())
