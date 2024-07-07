import asyncio

from aiogram import Dispatcher
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram import F

import bot.settings.keyboard as kb
from bot.settings.keyboard import remove_keyboard, format_collection_list
from bot.settings.states import CollectionStates
from bot.settings.variables import db, executor
from bot.services.task_manager import task_manager


def register_favorite_handlers(dp: Dispatcher):
    """
    Редактирование избранных коллекций
    """
    import bot.services.favorite_service as favorite_service

    #
    @dp.message(F.text == "Избранное")
    async def favourites_list_handler(message: Message, state: FSMContext) -> None:
        """
        Выбор действия над избранными коллекциями
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        await message.answer('Выберите желаемое действие над избранными коллекциями.',
                             reply_markup=kb.favorite_collections_menu)
        await state.set_state(CollectionStates.favorites)

    @dp.message(F.text == "Посмотреть избранное", CollectionStates.favorites)
    async def show_handler(message: Message) -> None:
        """
        Просмотр избранной коллекции
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        user_id = message.from_user.id
        await remove_keyboard(message)
        await message.reply(
            "*Выберите избранную коллекцию для её просмотра*\n", reply_markup=await format_collection_list(
                db.get_list_favorites(user_id), 'show_favorite_'), parse_mode='Markdown')

    @dp.message(F.text == "Изменить название", CollectionStates.favorites)
    async def send_name_handler(message: Message) -> None:
        """
        Выбор избранной коллекции для смены названия
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        user_id = message.from_user.id
        await remove_keyboard(message)
        await message.answer("*Выберите избранную коллекцию для смены её названия*\n",
                             reply_markup=await format_collection_list(db.get_list_favorites(user_id),
                                                                       'name_favorite_'),
                             parse_mode='Markdown')

    @dp.message(F.text == "Добавить в избранное", CollectionStates.favorites)
    async def add_favorites_list_handler(message: Message) -> None:
        """
        Выбор коллекции для добавления в избранное
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        user_id = message.from_user.id
        await remove_keyboard(message)
        await message.reply(
            "*Выберите коллекцию для добавления в избранное*\n", reply_markup=await format_collection_list(
                db.get_list_favorites(user_id, False), 'add_favorite_'), parse_mode='Markdown')

    @dp.message(F.text == "Удалить из избранного", CollectionStates.favorites)
    async def del_favorites_list_handler(message: Message) -> None:
        """
        Выбор коллекции для удаления из избранного
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        user_id = message.from_user.id
        await remove_keyboard(message)
        await message.reply(
            "*Выберите коллекцию для удаления из избранного*\n", reply_markup=await format_collection_list(
                db.get_list_favorites(user_id), "delete_favorite_"), parse_mode='Markdown')

    @dp.message(F.text == "Выгрузить в PDF", CollectionStates.favorites)
    async def pdf_collections_handler(message: Message) -> None:
        """
        Выбор избранной коллекции для выгрузки в PDF-файл
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        user_id = message.from_user.id
        await remove_keyboard(message)
        await message.answer("*Выберите избранную коллекцию для выгрузки в PDF*\n",
                             reply_markup=await format_collection_list(db.get_list_favorites(user_id), 'pdf_favorite_'),
                             parse_mode='Markdown')

    @dp.callback_query(lambda c: c.data.startswith("add_favorite_") or c.data.startswith("delete_favorite_"))
    async def edit_favorite_handler(callback_query: CallbackQuery) -> None:
        """
        Изменение флага избранности для выбранной коллекции
        """
        db.log_user_activity(callback_query.from_user.id, callback_query.inline_message_id)
        task_manager.create_loading_task(callback_query.message.chat.id, f'task_{callback_query.from_user.id}')

        is_favorite = callback_query.data.startswith("add_favorite_")
        collection_id, name = await favorite_service.get_collection_info(callback_query, is_favorite)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(executor, db.edit_favorites, collection_id, is_favorite)
        await favorite_service.send_favorite_status_message(callback_query, name, is_favorite)

        await task_manager.cancel_task_by_name(f'task_{callback_query.from_user.id}')
