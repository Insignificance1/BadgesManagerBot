import logging
from numpy.compat import long

from aiogram import Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

import bot.settings.keyboard as kb
from bot.settings.states import ManagerStates
from bot.settings.variables import db


def register_start_handlers(dp: Dispatcher):
    """
    Редактирование всех коллекций
    """
    @dp.message(CommandStart())
    async def command_start_handler(message: Message, state: FSMContext) -> None:
        """
        Знакомство с пользователем или менеджером
        """
        # Добавляем пользователя в БД
        user_id: long = message.from_user.id
        user_full_name = message.from_user.full_name
        logging.info(f'{user_id=} {user_full_name=}')
        db.log_user_activity(message.from_user.id, message.message_id)
        db.add_user(user_id)
        role = db.get_role(user_id)
        if role[0] == 'manager':
            # Знакомство с менеджером
            await state.set_state(ManagerStates.manager)
            await message.answer(f"Привет, Менеджер {user_full_name}! Я бот для работы с коллекционными значками.",
                                 reply_markup=kb.manager_menu)
        else:
            # Знакомство с пользователем
            main_menu = kb.create_main_menu(message.from_user.id)
            await message.answer(f"Привет, {user_full_name}! Я бот для работы с коллекционными значками.",
                                 reply_markup=main_menu)

    @dp.message(F.text == "Войти как пользователь", ManagerStates.manager)
    async def manager_to_user_handler(message: Message) -> None:
        db.log_user_activity(message.from_user.id, message.message_id)
        main_menu = kb.create_main_menu(message.from_user.id)
        await message.answer("Вам доступен функционал пользователя, чтобы вернуться к возможностям менеджера нажмите: "
                             "*Выйти*.",
                             reply_markup=main_menu,
                             parse_mode='Markdown')

    @dp.message(F.text == "Войти как менеджер", ManagerStates.manager)
    async def manager_handler(message: Message, state: FSMContext) -> None:
        db.log_user_activity(message.from_user.id, message.message_id)
        await state.set_state(ManagerStates.manager)
        await message.answer("Вам доступен функционал менеджера, чтобы вернуться к возможностям пользователя нажмите: "
                             "*Выйти*.",
                             reply_markup=kb.manager_function_menu,
                             parse_mode='Markdown')