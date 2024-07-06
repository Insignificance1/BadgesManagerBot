from aiogram import types
from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramBadRequest

from bot.settings.states import ImageStates
import bot.settings.keyboard as kb
from bot.settings.keyboard import create_edit_keyboard
from bot.settings.variables import bot, db


async def handle_prev_action(state, edit_idx):
    """
    Предыдущее изображение
    """
    edit_idx = max(edit_idx - 1, 0)
    await update_state_data(state, edit_idx)
    return edit_idx


async def handle_next_action(state, edit_idx):
    """
    Следующее изображение
    """
    edit_idx += 1
    await update_state_data(state, edit_idx)
    return edit_idx


async def handle_delete_action(images, edit_idx):
    """
    Удаление изображения
    """
    db.delete_image(images[edit_idx])
    del images[edit_idx]
    edit_idx = max(edit_idx - 1, 0)
    return edit_idx


async def handle_name_action(callback_query, state, edit_idx, data):
    """
    Смена названия изображения
    """
    if len(data.get('mes_to_del')) > 0:
        return
    mes = await bot.send_message(chat_id=callback_query.message.chat.id, text="Введите новое название значка.")
    mes_to_del = [mes.message_id]
    await state.set_state(ImageStates.waiting_for_image_name)
    await state.update_data(edit_idx=edit_idx, cq_id=callback_query.id, user=callback_query.from_user,
                            chat_ins=callback_query.chat_instance, cq_mes=callback_query.message,
                            mes_to_del=mes_to_del)


async def handle_count_action(callback_query, state, edit_idx, data):
    """
    Смена количества текущих значков
    """
    if len(data.get('mes_to_del')) > 0:
        return
    mes = await bot.send_message(chat_id=callback_query.message.chat.id, text="Введите количество значков.")
    mes_to_del = [mes.message_id]
    await state.set_state(ImageStates.waiting_for_image_count)
    await state.update_data(edit_idx=edit_idx, cq_id=callback_query.id, user=callback_query.from_user,
                            chat_ins=callback_query.chat_instance, cq_mes=callback_query.message,
                            mes_to_del=mes_to_del)


async def handle_exit_action(callback_query):
    """
    Выход
    """
    await bot.send_message(chat_id=callback_query.message.chat.id, text="Вы вернулись в главное меню.",
                           reply_markup=kb.main_menu)
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await callback_query.answer()


async def update_state_data(state, edit_idx):
    """
    Обновление edit_idx
    """
    await state.update_data(edit_idx=edit_idx)


async def edit_image_message(callback_query, images, edit_idx):
    """
    Обновление изображения
    """
    image_path = images[edit_idx]
    edit_keyboard = create_edit_keyboard(edit_idx, len(images))
    photo_aligned = FSInputFile(str(image_path))
    name = db.get_image_name(image_path)[0]
    count = db.get_image_count(image_path)[0]
    try:
        await bot.edit_message_media(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            media=types.InputMediaPhoto(media=photo_aligned,
                                        caption=f'ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ\nНазвание: {name}\nКоличество: {count}'),
            reply_markup=edit_keyboard
        )
    except TelegramBadRequest:
        print('[Ошибка] Ничего не поменялось, но на самом деле это не так.')


async def delete_old_messages(chat_id: int, messages_to_delete: list):
    """
    Удаление старых сообщений
    """
    for message_id in messages_to_delete:
        await bot.delete_message(chat_id, message_id)