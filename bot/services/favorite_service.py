from aiogram.types import CallbackQuery

import bot.settings.keyboard as kb
from bot.settings.variables import bot
from bot.services.other_service import get_collection_id_and_name


async def get_collection_info(callback_query: CallbackQuery, is_favorite: bool) -> tuple:
    """
    Получение id коллекции и её названия
    """
    type_id = 3 if is_favorite else 2
    collection_id, name = await get_collection_id_and_name(callback_query, type_id=type_id)
    return collection_id, name


async def send_favorite_status_message(callback_query: CallbackQuery, name: str, is_favorite: bool) -> None:
    """
    Отправка уведомления пользователю о смене флага избранности
    """
    await bot.delete_message(chat_id=callback_query.message.chat.id,
                             message_id=callback_query.message.message_id)
    if is_favorite:
        await callback_query.message.answer(f"Коллекция {name} успешно добавлена в избранное.",
                                            reply_markup=kb.favorite_collections_menu)
    else:
        await callback_query.message.answer(f"Коллекция {name} удалена из избранного.",
                                            reply_markup=kb.favorite_collections_menu)