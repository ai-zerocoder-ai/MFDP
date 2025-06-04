## Tiny Tattoos

AI-сервис для генерации татуировок в стиле **одной линии** по короткому текстовому описанию. Основан на генеративной диффузионной модели семейства flux, дообученной с помощью **LoRA (Low-Rank Adaptation)** - 

Обучение и улучшение моделей и получение файлов весов подробно представлено: 

https://colab.research.google.com/drive/1GSMVLvD6l9hgzCY03RDzNGAs76LQO5hl?usp=sharing

https://drive.google.com/file/d/1aWbNPpi_OD6EurJ7LVUeQyFcZnzA1xBR/view?usp=sharing

---

### Стек технологий

- **Backend:** Django
- **Celery:** асинхронные задачи генерации
- **RabbitMQ:** брокер сообщений
- **PostgreSQL:** база данных
- **Telegram Bot:** пользовательский интерфейс (на aiogram)
- **Nginx:** прокси (в разработке)
- **Docker Compose:** контейнеризация и управление сервисами

---

### Быстрый старт (Task_6)

```bash
cd docker
docker-compose up -d --build
```

После старта:

    Админка Django: http://localhost:8000/admin

    RabbitMQ UI: http://localhost:15672

### Как работает сервис:

    Пользователь стартует Telegram бота - telegram_id записывается в БД
    
    Пользователь вводит prompt в Telegram боте.

    Бот проверяет количество токенов пользователя.

    Celery-воркер запускает задачу генерации эскиза тату.

    Сгенерированное изображение сохраняется в формате PNG в общую директорию backend/temp_images/.

    Бот находит в директории PNG и отправляет его пользователю в бота.

    Сервис сохраняет результат в базе и списывает токены.
    
#### Примечания:

    LoRA-модель встроена в Celery-воркер и загружается при старте.

    Все данные пользователя (история генераций, токены) хранятся в базе PostgreSQL.

<h4>Скриншоты интерфейса Telegram-бота:</h4>

<p><strong>Главное меню</strong></p>
<img src="https://github.com/ai-zerocoder-ai/MFDP/blob/main/Task_6/Tiny_Tattoos_UI/main_menu.png?raw=true" width="400" style="margin-bottom: 24px;">

<p><strong>Описание сервиса</strong></p>
<img src="https://github.com/ai-zerocoder-ai/MFDP/blob/main/Task_6/Tiny_Tattoos_UI/about.png?raw=true" width="400" style="margin-bottom: 24px;">

<p><strong>Сгенерированный эскиз</strong></p>
<img src="https://github.com/ai-zerocoder-ai/MFDP/blob/main/Task_6/Tiny_Tattoos_UI/result.png?raw=true" width="400" style="margin-bottom: 24px;">
