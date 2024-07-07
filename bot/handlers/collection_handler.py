import asyncio

from aiogram import Dispatcher
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram import F

import bot.settings.keyboard as kb
from bot.settings.keyboard import remove_keyboard, format_collection_list
from bot.settings.states import CollectionStates
from bot.services.other_service import get_collection_id_and_name
from bot.settings.variables import bot, db, executor
from bot.services.task_manager import task_manager


def register_collection_handlers(dp: Dispatcher):
    """
    Редактирование изображений
    """
    import bot.services.collection_service as collection_service

    @dp.message(F.text == "Коллекции")
    async def collections_handler(message: Message) -> None:
        """
        Выбор действия над коллекциями
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        await message.reply("Выберите в меню желаемое действие.", reply_markup=kb.collections_menu)

    @dp.message(F.text == "Весь список")
    async def all_list_handler(message: Message, state: FSMContext) -> None:
        """
        Выбор действия над списком коллекций
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        await message.answer('Выберите желаемое действие над всем списком коллекций.',
                             reply_markup=kb.all_collections_menu)
        await state.set_state(CollectionStates.collections)

    @dp.message(F.text == "Добавить коллекцию")
    async def add_handler(message: Message, state: FSMContext) -> None:
        """
        Ожидание архива с изображениями при создании коллекции
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        await message.reply("Отправьте ZIP-файл с изображениями.", reply_markup=kb.back_menu)
        await state.set_state(CollectionStates.waiting_for_zip_create)

    @dp.message(F.document, CollectionStates.waiting_for_zip_create)
    async def get_zip_handler(message: Message, state: FSMContext) -> None:
        """
        Ожидание ввода названия новой коллекции
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        await state.update_data(zip_file_id=message.document.file_id)
        await message.reply("Файл получен. Введите название новой коллекции.", reply_markup=kb.back_menu)
        await state.set_state(CollectionStates.add_new_collection_zip_name)

    @dp.message(F.text, CollectionStates.add_new_collection_zip_name)
    async def create_collection_handler(message: Message, state: FSMContext) -> None:
        """
        Создание коллекции
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        # Запускаем параллельную задачу для режима ожидания
        task_manager.create_loading_task(message.chat.id, f'task_{message.from_user.id}')
        data = await state.get_data()
        zip_file_id = data.get('zip_file_id')
        # Добавляем коллекцию в БД
        collection_name = message.text
        collection_id = await collection_service.try_add_collection(message, collection_name)

        if collection_id:
            await collection_service.process_and_finalise_zip_file(message, zip_file_id,
                                                                   collection_id, collection_name)
        await state.clear()

    @dp.message(F.text == "Удалить коллекцию")
    async def delete_collection_handler(message: Message) -> None:
        """
        Выбор коллекции для удаления
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        user_id = message.from_user.id
        await remove_keyboard(message)
        await message.answer("*Выберите коллекцию для её удаления*\n",
                             reply_markup=await format_collection_list(db.get_list_collection(user_id),
                                                                       'delete_collection_'),
                             parse_mode='Markdown')

    @dp.callback_query(lambda c: c.data.startswith("delete_collection_"))
    async def delete_collection_number_handler(callback_query: CallbackQuery) -> None:
        """
        Удаление коллекции
        """
        db.log_user_activity(callback_query.from_user.id, callback_query.inline_message_id)
        # Запускаем параллельную задачу для режима ожидания
        task_manager.create_loading_task(callback_query.message.chat.id, f'task_{callback_query.from_user.id}')
        loop = asyncio.get_running_loop()
        # Получаем id коллекции
        collection_id = (await get_collection_id_and_name(callback_query, loop, 1))[0]
        await loop.run_in_executor(executor, db.delete_collection, callback_query.from_user.id, collection_id)
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await callback_query.message.answer("Коллекция успешно удалена.", reply_markup=kb.collections_menu)
        # Завершаем режим ожидания
        await task_manager.cancel_task_by_name(f'task_{callback_query.from_user.id}')

    @dp.message(F.text == "Изменить название", CollectionStates.collections)
    async def send_name_handler(message: Message) -> None:
        """
        Выбор коллекции для смены названия
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        user_id = message.from_user.id
        await remove_keyboard(message)
        await message.answer("*Выберите коллекцию для смены её названия*\n",
                             reply_markup=await format_collection_list(db.get_list_collection(user_id),
                                                                       'name_collection_'),
                             parse_mode='Markdown')

    @dp.callback_query(lambda c: c.data.startswith("name_collection_") or c.data.startswith("name_favorite_"))
    async def change_name_handler(callback_query: CallbackQuery, state: FSMContext) -> None:
        """
        Ожидание ввода названия коллекции
        """
        db.log_user_activity(callback_query.from_user.id, callback_query.inline_message_id)
        type_id = 2 if callback_query.data.startswith("name_favorite_") else 1
        collection_id, name = await get_collection_id_and_name(callback_query, type_id=type_id)
        await callback_query.message.answer("Просим вас ввести новое название для коллекции.",
                                            reply_markup=kb.back_menu)
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await state.update_data(collection_id=collection_id)
        await state.set_state(CollectionStates.waiting_for_name_collection)

    @dp.message(CollectionStates.waiting_for_name_collection)
    async def new_name_handler(message: Message, state: FSMContext) -> None:
        """
        Смена названия коллекции
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        new_name = message.text
        data = await state.get_data()
        collection_id = data['collection_id']
        user_id = message.from_user.id
        try:
            # Обновляем название коллекции
            reply = db.update_collection_name(user_id, new_name, collection_id)
            await message.reply(reply, reply_markup=kb.all_collections_menu)
            await state.clear()
            await state.set_state(CollectionStates.collections)
        except Exception as e:
            await message.reply(str(e) + '\nПопробуйте ещё раз.')
            await CollectionStates.waiting_for_name_collection.set()

    @dp.message(F.text == "Посмотреть коллекцию", CollectionStates.collections)
    async def show_handler(message: Message, state: FSMContext) -> None:
        """
        Просмотр коллекции
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        user_id = message.from_user.id
        await remove_keyboard(message)
        await state.update_data(edit_idx=0)
        await message.reply(
            "*Выберите коллекцию для её просмотра*\n", reply_markup=await format_collection_list(
                db.get_list_collection(user_id), 'show_collection_'), parse_mode='Markdown')

    @dp.message(F.text == "Пополнить коллекцию", CollectionStates.collections)
    async def add_handler(message: Message) -> None:
        """
        Выбор коллекции для пополнения
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        user_id = message.from_user.id
        await remove_keyboard(message)
        await message.reply(
            "*Выберите коллекцию для её пополнения*\n", reply_markup=await format_collection_list(
                db.get_list_collection(user_id), 'add_badges_'), parse_mode='Markdown')

    @dp.callback_query(lambda c: c.data.startswith("add_badges_"))
    async def wait_for_badges_handler(callback_query: CallbackQuery, state: FSMContext) -> None:
        """
        Ожидание архива с изображениями для пополнения коллекции
        """
        db.log_user_activity(callback_query.from_user.id, callback_query.inline_message_id)
        collection_id, name = await get_collection_id_and_name(callback_query, type_id=1)
        await callback_query.message.answer("Отправьте ZIP-файл с изображениями.", reply_markup=kb.back_menu)
        await state.update_data(collection_id=collection_id, collection_name=name)
        await state.set_state(CollectionStates.waiting_for_zip_add)
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)

    @dp.message(F.document, CollectionStates.waiting_for_zip_add)
    async def add_badges_handler(message: Message, state: FSMContext) -> None:
        """
        Пополнение коллекции
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        # Подтверждаем получение файла
        await message.reply("Файл получен.", reply_markup=kb.back_menu)
        # Запускаем параллельную задачу для режима ожидания
        task_manager.create_loading_task(message.chat.id, f'task_{message.from_user.id}')
        # Извлекаем данные из состояния
        data = await state.get_data()
        collection_id = data.get('collection_id')
        collection_name = data.get('collection_name')
        zip_file_id = message.document.file_id
        # Обрабатываем архив
        await collection_service.handle_zip_processing(message, collection_id, collection_name, zip_file_id, state)

    @dp.message(F.text == "Вывести недостающие значки", CollectionStates.collections)
    async def null_badges_list_handler(message: Message, state: FSMContext) -> None:
        """
        Вывод недостающих значков
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        await state.set_state(CollectionStates.state_null_badges)
        await pdf_collections_handler(message)

    @dp.message(F.text == "Выгрузить в PDF", CollectionStates.collections)
    async def pdf_collections_handler(message: Message) -> None:
        """
        Выбор коллекции для выгрузки в PDF-файл
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        user_id = message.from_user.id
        await remove_keyboard(message)
        await message.answer("*Выберите коллекцию для выгрузки в PDF*\n",
                             reply_markup=await format_collection_list(db.get_list_collection(user_id),
                                                                       'pdf_collection_'),
                             parse_mode='Markdown')

    @dp.message(F.text == "Выгрузить в PDF", CollectionStates.state_null_badges)
    async def pdf_collections_handler(message: Message) -> None:
        """
        Выбор коллекции для выгрузки в PDF-файл недостающих значков
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        user_id = message.from_user.id
        await remove_keyboard(message)
        await message.answer("*Выберите коллекцию для выгрузки в PDF*\n",
                             reply_markup=await format_collection_list(db.get_list_collection(user_id), 'pdf_null_'),
                             parse_mode='Markdown')

    @dp.callback_query(lambda c: c.data.startswith("pdf_collection_") or c.data.startswith("pdf_favorite_") or
                                 c.data.startswith("pdf_null_"))
    async def send_pdf(callback_query: CallbackQuery, state: FSMContext) -> None:
        """
        Выгрузка в PDF-файл выбранной коллекции
        """
        db.log_user_activity(callback_query.from_user.id, callback_query.inline_message_id)
        task_manager.create_loading_task(callback_query.message.chat.id, f'task_{callback_query.from_user.id}')

        loop = asyncio.get_running_loop()
        type_id, null_or_all_images, is_all_count = collection_service.determine_type_and_images(callback_query.data)
        collection_id, name = await get_collection_id_and_name(callback_query, type_id=type_id)

        images_list, count_list, name_list = await collection_service.fetch_collection_data(loop,
                                                                                            null_or_all_images,
                                                                                            collection_id,
                                                                                            is_all_count)
        pdf_path = await collection_service.convert_to_pdf(loop, name, collection_id, images_list, name_list, count_list)

        await collection_service.send_pdf_to_user(callback_query, state, pdf_path)
        await task_manager.cancel_task_by_name(f'task_{callback_query.from_user.id}')
