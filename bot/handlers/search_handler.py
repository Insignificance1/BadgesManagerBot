from aiogram import Dispatcher
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram import F

from bot.settings.states import SearchStates
from bot.settings.keyboard import remove_keyboard, format_collection_list_id, format_image_list
from bot.settings.variables import db
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
