import re
from datetime import datetime

from aiogram import Dispatcher
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram import F

import bot.settings.keyboard as kb
from bot.settings.keyboard import remove_keyboard
from bot.settings.states import ManagerStates
from bot.settings.variables import bot, db


def register_statistics_handlers(dp: Dispatcher):
    """
    Статистика нагрузки и новых пользователей
    """
    import bot.services.statistics_service as statistics_service

    @dp.message(F.text == "Статистика нагрузки", ManagerStates.manager)
    async def workload_handler(message: Message, state: FSMContext) -> None:
        """
        Выбор просмотра статистики нагрузки за период или за всё время
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        await state.set_state(ManagerStates.manager_workload)
        await message.answer("Выберите:",
                             reply_markup=kb.time_menu,
                             parse_mode='Markdown')

    @dp.message(F.text == "За период", ManagerStates.manager_workload)
    async def period_handler(message: Message, state: FSMContext) -> None:
        """
        Выбор периода статистики нагрузки
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        await remove_keyboard(message)
        await state.set_state(ManagerStates.input_period_workload)
        await message.answer("Введите начальную и конечную дату в формате: _Год-Месяц-День_ : _Год-Месяц-День_",
                             reply_markup=kb.back_menu,
                             parse_mode='Markdown')

    @dp.message(F.text == "За все время", ManagerStates.manager_workload)
    async def all_time_handler(message: Message, state: FSMContext) -> None:
        """
        Обработка и отправка статистики нагрузки за всё время
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        user_id = message.from_user.id
        d_start_date = datetime(year=2024, month=7, day=1,
                                hour=0, minute=0, second=0)
        d_end_date = datetime.now()
        # Получение статистики нагрузки
        list_date = db.get_workload_stats(d_start_date, d_end_date)
        path = await statistics_service.generate_user_statistics(list_date, user_id, 1)
        graphic = FSInputFile(path)
        # Отправка фото статистики нагрузки
        await bot.send_photo(chat_id=message.chat.id, photo=graphic, reply_markup=kb.manager_function_menu)
        await state.clear()
        await state.set_state(ManagerStates.manager)

    @dp.message(F.text == "Статистика новых пользователей", ManagerStates.manager)
    async def manager_to_user_handler(message: Message, state: FSMContext) -> None:
        """
        Выбор просмотра статистики новых пользователей за период или за всё время
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        await state.set_state(ManagerStates.manager_new_user)
        await message.answer("Выберите:",
                             reply_markup=kb.time_menu,
                             parse_mode='Markdown')

    @dp.message(F.text == "За период", ManagerStates.manager_new_user)
    async def period_handler(message: Message, state: FSMContext) -> None:
        """
        Выбор периода статистики новых пользователей
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        await remove_keyboard(message)
        await state.set_state(ManagerStates.input_period_new_users)
        await message.answer("Введите начальную и конечную дату в формате: _Год-Месяц-День_ : _Год-Месяц-День_",
                             reply_markup=kb.back_menu,
                             parse_mode='Markdown')

    @dp.message(F.text == "За все время", ManagerStates.manager_new_user)
    async def all_time_handler(message: Message, state: FSMContext) -> None:
        """
        Обработка и отправка статистики нагрузки за всё время
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        user_id = message.from_user.id
        d_start_date = datetime(year=2024, month=7, day=1,
                                hour=0, minute=0, second=0)
        d_end_date = datetime.now()
        list_date = db.get_users_stats(d_start_date, d_end_date)
        path = await statistics_service.generate_user_statistics(list_date, user_id, 0)
        graphic = FSInputFile(path)
        await bot.send_photo(chat_id=message.chat.id, photo=graphic, reply_markup=kb.manager_function_menu)
        await state.clear()
        await state.set_state(ManagerStates.manager)

    @dp.message(F.text, ManagerStates.input_period_new_users)
    @dp.message(F.text, ManagerStates.input_period_workload)
    async def period_time_handler(message: Message, state: FSMContext) -> None:
        """
        Обработка и отправка статистики за период
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        date = message.text

        # Проверяем, не хочет ли пользователь вернуться в предыдущее меню
        if await statistics_service.handle_back_action(message, state, date):
            return
        # Проверяем, корректен ли формат введенных дат
        date_parts = date.split(" : ")
        if await statistics_service.handle_invalid_format(message, date_parts):
            return
        # Проверяем, корректны ли сами даты
        start_date, end_date = date_parts
        if await statistics_service.handle_invalid_dates(message, start_date, end_date):
            return

        # Определяем, какую статистику нужно получить
        d_start_date, d_end_date = statistics_service.parse_dates(start_date, end_date)
        is_new_users = await state.get_state() == ManagerStates.input_period_new_users
        if is_new_users:
            list_date = db.get_users_stats(d_start_date, d_end_date)
        else:
            list_date = db.get_workload_stats(d_start_date, d_end_date)

        # Если данные не найдены, уведомляем пользователя
        if not list_date:
            await message.answer(
                "*Ошибка*: По данному периоду ничего не найдено, введите корректную дату",
                reply_markup=kb.back_menu,
                parse_mode='Markdown'
            )
            return

        # Генерируем статистику и отправляем пользователю
        user_stat_type = 0 if is_new_users else 1
        path = await statistics_service.generate_user_statistics(list_date, message.from_user.id, user_stat_type)
        graphic = FSInputFile(path)

        await bot.send_photo(chat_id=message.chat.id, photo=graphic, reply_markup=kb.manager_function_menu)
        await state.clear()
        await state.set_state(ManagerStates.manager)
