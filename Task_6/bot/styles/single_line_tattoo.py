import logging
from pathlib import Path
from typing import List, Dict, Any

from aiogram.types import Message
from styles.base import TattooStyle

logger = logging.getLogger(__name__)

# Директория для временных изображений (ту же, что и у воркера)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMP_DIR = BASE_DIR / "backend" / "temp_images"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


class SingleLineTattooStyle(TattooStyle):
    """
    Заглушка для «Single Line Tattoo». Реальная генерация перенесена в Celery‐таск
    generate_single_line_task. Метод generate() здесь больше не вызывает fal_client.run.
    """

    async def generate(self, message: Message, data: Dict[str, Any]) -> List[str]:
        """
        Этот метод не используется в боте: вместо него вызывается Celery‐таск
        в handlers/generation.py. Если он всё же будет вызван, сразу возвращает [].
        """
        logger.warning("SingleLineTattooStyle.generate вызван напрямую, а не через Celery.")
        return []
