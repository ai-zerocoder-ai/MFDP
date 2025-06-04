import io
import random
import time
from pathlib import Path
from typing import List

import httpx
from PIL import Image
import fal_client
from celery import shared_task
from django.conf import settings

# Папка для временных изображений (ту же, что и у бота)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMP_DIR = BASE_DIR / "temp_images"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

@shared_task(name="apps.generations.tasks.generate_single_line_task")
def generate_single_line_task(telegram_id: int, prompt_text: str) -> List[str]:
    """
    Фоновая задача Celery:
    1) Собираем параметры из Django settings.
    2) Вызываем fal_client.run, скачиваем картинку, сохраняем PNG.
    3) Возвращаем список путей к файлам PNG.
    """
    try:
        # Берём все нужные константы из settings.py
        MODEL = settings.MODEL
        LORA = settings.LORA
        TRIG = settings.TRIG

        args = {
            "prompt": f"{TRIG} {prompt_text}",
            "image_size": {"width": 512, "height": 512},
            "num_inference_steps": 45,
            "guidance_scale": 4.8,
            "seed": random.randint(1, 1_000_000_000),
            "loras": [{"path": LORA, "scale": 1.1}],
        }

        # Вызываем fal_client.run синхронно (воркер работает в отдельном процессе)
        result = fal_client.run(MODEL, arguments=args)
        if not result or not result.get("images"):
            raise ValueError("Некорректный ответ от API генерации")

        image_url = result["images"][0].get("url")
        if not image_url:
            raise ValueError("URL изображения не найден в ответе API")

        # Скачиваем изображение
        resp = httpx.get(image_url, timeout=30.0)
        resp.raise_for_status()
        img_data = io.BytesIO(resp.content)
        img = Image.open(img_data).convert("RGB")

        # Сохраняем PNG в папку temp_images
        filename = TEMP_DIR / f"single_line_{telegram_id}_{int(time.time())}.png"
        img.save(filename, format="PNG")

        return [str(filename)]

    except Exception:
        # В случае ошибки просто возвращаем пустой список
        return []
