import logging
from typing import Union, Optional

from aiogram.types import Message, CallbackQuery, InputMediaPhoto, InlineKeyboardMarkup, FSInputFile
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)


async def swap_card(
    origin: Union[Message, CallbackQuery],
    state: FSMContext,
    new_photo_path: Optional[str] = None,
    new_caption: str = "",
    new_kb: Optional[InlineKeyboardMarkup] = None
):
    """
    Обновляет «главную» карточку в чате: редактирует существующее сообщение,
    либо отправляет новое, если редактировать нельзя или сообщения ещё нет.

    Параметры:
      - origin: либо Message, либо CallbackQuery, от которого берём bot и chat_id
      - state: FSMContext для хранения/извлечения main_msg_id
      - new_photo_path: путь к новому изображению (если None, будет редактировать/отправлять только текст)
      - new_caption: текст для подписи/сообщения (HTML-парсинг)
      - new_kb: inline-клавиатура для сообщения
    """
    try:
        data = await state.get_data()
        bot = origin.bot
        # Определяем chat_id в зависимости от типа origin
        if isinstance(origin, Message):
            chat_id = origin.chat.id
        else:  # CallbackQuery
            chat_id = origin.message.chat.id

        main_msg_id = data.get("main_msg_id")

        # Если main_msg_id ещё не сохранён — отправляем новое сообщение и сохраняем его ID
        if not main_msg_id:
            if new_photo_path:
                try:
                    sent = await bot.send_photo(
                        chat_id=chat_id,
                        photo=FSInputFile(new_photo_path),
                        caption=new_caption,
                        reply_markup=new_kb,
                    )
                except Exception as e:
                    logger.error(f"Failed to send initial photo: {e}", exc_info=True)
                    # Попробуем отправить как текст, если фото по какой-то причине не отправляется
                    sent = await bot.send_message(
                        chat_id=chat_id,
                        text=new_caption,
                        reply_markup=new_kb,
                    )
            else:
                sent = await bot.send_message(
                    chat_id=chat_id,
                    text=new_caption,
                    reply_markup=new_kb,
                )
            await state.update_data(main_msg_id=sent.message_id)
            return

        # Попытка редактирования уже существующего сообщения
        try:
            if new_photo_path:
                media = InputMediaPhoto(
                    media=FSInputFile(new_photo_path),
                    caption=new_caption,
                    parse_mode="HTML",
                )
                await bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=main_msg_id,
                    media=media,
                    reply_markup=new_kb,
                )
            else:
                await bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=main_msg_id,
                    caption=new_caption,
                    parse_mode="HTML",
                    reply_markup=new_kb,
                )
        except TelegramBadRequest as tb:
            # Если нельзя редактировать (например, устарело, или меняем тип media),
            # отправляем новую карточку и обновляем main_msg_id
            logger.warning(f"Edit failed (TelegramBadRequest): {tb}; sending new message instead.")
            if new_photo_path:
                sent = await bot.send_photo(
                    chat_id=chat_id,
                    photo=FSInputFile(new_photo_path),
                    caption=new_caption,
                    reply_markup=new_kb,
                )
            else:
                sent = await bot.send_message(
                    chat_id=chat_id,
                    text=new_caption,
                    reply_markup=new_kb,
                )
            await state.update_data(main_msg_id=sent.message_id)

    except Exception as e:
        logger.error(f"swap_card unexpected error: {e}", exc_info=True)
        raise
