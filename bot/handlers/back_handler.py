from aiogram import Dispatcher
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram import F

import bot.settings.keyboard as kb
from bot.settings.states import ManagerStates
from bot.settings.variables import bot, db


def register_back_handlers(dp: Dispatcher):
    """
    Выход в главное меню
    """
    @dp.message(F.text == "Назад", ManagerStates.manager)
    @dp.message(F.text == "Назад", ManagerStates.manager_new_user)
    @dp.message(F.text == "Назад", ManagerStates.manager_workload)
    async def back_handler(message: Message, state: FSMContext) -> None:
        """
        Выход менеджера в главное меню
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        await state.clear()
        await state.set_state(ManagerStates.manager)
        await message.reply("Вы вернулись в главное меню.", reply_markup=kb.manager_function_menu)

    @dp.message(F.text == "Выход")
    async def back_handler(message: Message, state: FSMContext) -> None:
        """
        Выход менеджера к выбору роли
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        await state.clear()
        await state.set_state(ManagerStates.manager)
        await message.reply("Вы вернулись в главное меню.", reply_markup=kb.manager_menu)

    @dp.message(F.text == "Назад")
    async def back_handler(message: Message, state: FSMContext) -> None:
        """
        Возвращение в главное меню для ReplyKeyboard
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        await state.clear()
        main_menu = kb.create_main_menu(message.from_user.id)
        await message.reply("Вы вернулись в главное меню.", reply_markup=main_menu)

    @dp.callback_query(lambda c: c.data == "main_menu")
    async def process_callback(callback_query: CallbackQuery) -> None:
        """
        Возвращение в главное меню для InlineKeyboard
        """
        main_menu = kb.create_main_menu(callback_query.from_user.id)
        await callback_query.message.answer("Вы вернулись в главное меню.", reply_markup=main_menu)
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
