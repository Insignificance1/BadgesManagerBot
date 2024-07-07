from aiogram import Dispatcher
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram import F

from bot.settings.states import SearchStates
from bot.settings.keyboard import remove_keyboard, format_collection_list_id, format_image_list, create_edit_keyboard
from bot.settings.variables import bot, db
from bot.services.task_manager import task_manager


def register_search_handlers(dp: Dispatcher):
    """
    Поиск коллекций и значков
    """
    @dp.message(F.text == "Поиск")
    async def search_handler(message: Message, state: FSMContext) -> None:
        """
        Ожидание ввода названия коллекции или значка
        """
        await remove_keyboard(message)
        await message.answer("Введите название коллекции или значка.")
        await state.set_state(SearchStates.waiting_for_search)

    @dp.message(F.text, SearchStates.waiting_for_search)
    async def search(message: Message, state: FSMContext) -> None:
        """
        Поиск коллекций и значков
        """
        # Запускаем параллельную задачу для режима ожидания
        task_manager.create_loading_task(message.chat.id, f'task_{message.from_user.id}')
        user_id = message.from_user.id
        search_query = message.text
        await message.answer("*Результаты поиска\nКоллекции:\n*",
                             reply_markup=await format_collection_list_id(db.get_list_collection_for_name(user_id,
                                                                                                          search_query),
                                                                          'search_collection_'),
                             parse_mode='Markdown')
        await message.answer("*Значки:\n*",
                             reply_markup=await format_image_list(db.get_all_images_for_name(user_id, search_query),
                                                                  'show_badge_'),
                             parse_mode='Markdown')
        await task_manager.cancel_task_by_name(f'task_{message.from_user.id}')
        await state.clear()

    @dp.callback_query(lambda c: c.data.startswith('search_collection_'))
    async def process_edit_callback(callback_query: CallbackQuery, state: FSMContext) -> None:
        """
        Создание inline клавиатуры для редактирования изображений
        """
        db.log_user_activity(callback_query.from_user.id, callback_query.inline_message_id)
        # Получаем id и название коллекции
        collection_id = int(callback_query.data.split("_")[2])
        # Получаем изображения в выбранной коллекции
        images = db.get_all_images(collection_id)
        # Преобразуем результат запроса в список путей
        formatted_images = [row[0] for row in images]
        # Отправляем inline клавиатуру с первым изображением
        name = db.get_image_name(formatted_images[0])[0]
        count = db.get_image_count(formatted_images[0])[0]
        await bot.send_photo(chat_id=callback_query.message.chat.id, photo=FSInputFile(str(formatted_images[0])),
                             reply_markup=create_edit_keyboard(0, len(formatted_images)),
                             caption=f'ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ\n1/{len(formatted_images)}'
                                     f'\nНазвание: {name}\nКоличество: {count}')
        await bot.delete_message(chat_id=callback_query.message.chat.id,
                                 message_id=callback_query.message.message_id)
        await state.update_data(images=formatted_images, edit_idx=0, mes_to_del=[])

    @dp.callback_query(lambda c: c.data.startswith('show_badge_'))
    async def process_edit_image_callback(callback_query: CallbackQuery, state: FSMContext) -> None:
        """
        Создание inline клавиатуры для редактирования изображения
        """
        db.log_user_activity(callback_query.from_user.id, callback_query.inline_message_id)
        image_id = int(callback_query.data.split("_")[2])
        # Получаем изображение
        image = db.get_image(image_id)
        collection_id = db.get_id_collection_by_image(image_id)
        images = db.get_all_images(collection_id[0][0])
        formatted_images = [row[0] for row in images]
        for i, img in enumerate(formatted_images, start=1):
            img_id = db.get_image_id(img)[0]
            if image_id == img_id:
                image_id = i
        path = str(image[0][0])
        # Отправляем inline клавиатуру с первым изображением
        name = db.get_image_name(path)[0]
        count = db.get_image_count(path)[0]
        await bot.send_photo(chat_id=callback_query.message.chat.id, photo=FSInputFile(path),
                             reply_markup=create_edit_keyboard(image_id-1, len(formatted_images)),
                             caption=f'ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ\n{image_id}/{len(images)}'
                                     f'\nНазвание: {name}\nКоличество: {count}')
        await bot.delete_message(chat_id=callback_query.message.chat.id,
                                 message_id=callback_query.message.message_id)
        await state.update_data(images=formatted_images, edit_idx=image_id-1, mes_to_del=[])
