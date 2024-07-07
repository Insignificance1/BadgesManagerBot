import logging
import asyncio
import os
import re
from datetime import datetime

from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
from numpy.compat import long

from bot.settings import keyboard
from bot.settings.states import ManagerStates
from bot.settings.keyboard import remove_keyboard
from services.statistics_service import generate_user_statistics
from bot.settings.variables import bot, dp, db

from handlers.image_handler import register_image_handlers
from handlers.instruction_handler import register_instruction_handlers
from handlers.photo_handler import register_photo_handlers
from handlers.collection_handler import register_collection_handlers
from handlers.favorite_handler import register_favorite_handlers
from handlers.search_handler import register_search_handlers

register_image_handlers(dp)
register_instruction_handlers(dp)
register_photo_handlers(dp)
register_collection_handlers(dp)
register_favorite_handlers(dp)
register_search_handlers(dp)

# Настройка логирования
logging.basicConfig(level=logging.INFO)


# Знакомство с пользователем
@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    # Добавляем пользователя в БД
    user_id: long = message.from_user.id
    user_full_name = message.from_user.full_name
    logging.info(f'{user_id=} {user_full_name=}')
    db.log_user_activity(message.from_user.id, message.message_id)
    db.add_user(user_id)
    role = db.get_role(user_id)
    if role[0] == 'manager':
        await state.set_state(ManagerStates.manager)
        await message.answer(f"Привет, Менеджер {user_full_name}! Я бот для работы с коллекционными значками.",
                             reply_markup=keyboard.manager_menu)
    else:
        main_menu = keyboard.create_main_menu(message.from_user.id)
        await message.answer(f"Привет, {user_full_name}! Я бот для работы с коллекционными значками.",
                             reply_markup=main_menu)


@dp.message(F.text == "Войти как пользователь", ManagerStates.manager)
async def manager_to_user_handler(message: Message) -> None:
    db.log_user_activity(message.from_user.id, message.message_id)
    main_menu = keyboard.create_main_menu(message.from_user.id)
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
                         reply_markup=keyboard.manager_function_menu,
                         parse_mode='Markdown')


@dp.message(F.text == "Статистика нагрузки", ManagerStates.manager)
async def workload_handler(message: Message, state: FSMContext) -> None:
    db.log_user_activity(message.from_user.id, message.message_id)
    await state.set_state(ManagerStates.manager_workload)
    await message.answer("Выберите:",
                         reply_markup=keyboard.time_menu,
                         parse_mode='Markdown')


@dp.message(F.text == "За период", ManagerStates.manager_workload)
async def period_handler(message: Message, state: FSMContext) -> None:
    db.log_user_activity(message.from_user.id, message.message_id)
    await remove_keyboard(message)
    await state.set_state(ManagerStates.input_period_workload)
    await message.answer("Введите начальную и конечную дату в формате: _Год-Месяц-День_ : _Год-Месяц-День_",
                         reply_markup=keyboard.back_menu,
                         parse_mode='Markdown')


@dp.message(F.text == "За все время", ManagerStates.manager_workload)
async def all_time_handler(message: Message, state: FSMContext) -> None:
    db.log_user_activity(message.from_user.id, message.message_id)
    user_id = message.from_user.id
    d_start_date = datetime(year=2024, month=7, day=1,
                            hour=0, minute=0, second=0)
    d_end_date = datetime.now()
    list_date = db.get_workload_stats(d_start_date, d_end_date)
    path = await generate_user_statistics(list_date, user_id, 1)
    graphic = FSInputFile(path)
    await bot.send_photo(chat_id=message.chat.id, photo=graphic, reply_markup=keyboard.manager_function_menu)
    await state.clear()
    await state.set_state(ManagerStates.manager)


@dp.message(F.text, ManagerStates.input_period_workload)
async def period_time_workload_handler(message: Message, state: FSMContext) -> None:
    db.log_user_activity(message.from_user.id, message.message_id)
    date = message.text
    user_id = message.from_user.id
    date_parts = date.split(" : ")

    if date == "Назад":
        await state.clear()
        await state.set_state(ManagerStates.manager)
        await message.answer("Вернул вас в меню с функциями: ",
                             reply_markup=keyboard.manager_function_menu,
                             parse_mode='Markdown')
        return

    if len(date_parts) != 2:
        await message.answer(
            "*Ошибка*: Неверно указан формат, необходимо отправить период в следующем виде: _Год-Месяц-День_ : "
            "_Год-Месяц-День_",
            reply_markup=keyboard.back_menu,
            parse_mode='Markdown')
        return

    start_date, end_date = date_parts
    date_pattern = r"^\d{4}-\d{2}-\d{2}$"
    if not re.match(date_pattern, start_date) or not re.match(date_pattern, end_date):
        await message.answer(
            "*Ошибка*: Неверно указан формат, необходимо отправить период в следующем виде: _Год-Месяц-День_ : "
            "_Год-Месяц-День_",
            reply_markup=keyboard.back_menu,
            parse_mode='Markdown')
        return

    start_dates = start_date.split("-")
    end_dates = end_date.split("-")
    d_start_date = datetime(year=int(start_dates[0]), month=int(start_dates[1]), day=int(start_dates[2]),
                            hour=0, minute=0, second=0)
    d_end_date = datetime(year=int(end_dates[0]), month=int(end_dates[1]), day=int(end_dates[2]),
                          hour=23, minute=59, second=59)
    list_date = db.get_workload_stats(d_start_date, d_end_date)
    if not list_date:
        await message.answer(
            "*Ошибка*: По данному периоду ничего не найдено, введите корректную дату",
            reply_markup=keyboard.back_menu,
            parse_mode='Markdown')
        return

    path = await generate_user_statistics(list_date, user_id, 1)
    graphic = FSInputFile(path)
    await bot.send_photo(chat_id=message.chat.id, photo=graphic, reply_markup=keyboard.manager_function_menu)
    await state.clear()
    await state.set_state(ManagerStates.manager)


@dp.message(F.text == "Статистика новых пользователей", ManagerStates.manager)
async def manager_to_user_handler(message: Message, state: FSMContext) -> None:
    db.log_user_activity(message.from_user.id, message.message_id)
    await state.set_state(ManagerStates.manager_new_user)
    await message.answer("Статистика новых пользователей",
                         reply_markup=keyboard.time_menu,
                         parse_mode='Markdown')


@dp.message(F.text == "За период", ManagerStates.manager_new_user)
async def period_handler(message: Message, state: FSMContext) -> None:
    db.log_user_activity(message.from_user.id, message.message_id)
    await remove_keyboard(message)
    await state.set_state(ManagerStates.input_period_new_users)
    await message.answer("Введите начальную и конечную дату в формате: _Год-Месяц-День_ : _Год-Месяц-День_",
                         reply_markup=keyboard.back_menu,
                         parse_mode='Markdown')


@dp.message(F.text == "За все время", ManagerStates.manager_new_user)
async def all_time_handler(message: Message, state: FSMContext) -> None:
    db.log_user_activity(message.from_user.id, message.message_id)
    user_id = message.from_user.id
    d_start_date = datetime(year=2024, month=7, day=1,
                            hour=0, minute=0, second=0)
    d_end_date = datetime.now()
    list_date = db.get_users_stats(d_start_date, d_end_date)
    path = await generate_user_statistics(list_date, user_id, 0)
    graphic = FSInputFile(path)
    await bot.send_photo(chat_id=message.chat.id, photo=graphic, reply_markup=keyboard.manager_function_menu)
    await state.clear()
    await state.set_state(ManagerStates.manager)


@dp.message(F.text, ManagerStates.input_period_new_users)
async def period_time_handler(message: Message, state: FSMContext) -> None:
    db.log_user_activity(message.from_user.id, message.message_id)
    date = message.text
    user_id = message.from_user.id
    date_parts = date.split(" : ")

    if date == "Назад":
        await state.clear()
        await state.set_state(ManagerStates.manager)
        await message.answer("Вернул вас в меню с функциями: ",
                             reply_markup=keyboard.manager_function_menu,
                             parse_mode='Markdown')
        return

    if len(date_parts) != 2:
        await message.answer(
            "Ошибка: Неверно указан формат, необходимо отправить период в следующем виде: _Год-Месяц-День_ : "
            "_Год-Месяц-День_",
            reply_markup=keyboard.back_menu,
            parse_mode='Markdown')
        return

    start_date, end_date = date_parts
    date_pattern = r"^\d{4}-\d{2}-\d{2}$"
    if not re.match(date_pattern, start_date) or not re.match(date_pattern, end_date):
        await message.answer(
            "*Ошибка*: Неверно указан формат, необходимо отправить период в следующем виде: _Год-Месяц-День_ : "
            "_Год-Месяц-День_",
            reply_markup=keyboard.back_menu,
            parse_mode='Markdown')
        return

    start_dates = start_date.split("-")
    end_dates = end_date.split("-")
    d_start_date = datetime(year=int(start_dates[0]), month=int(start_dates[1]), day=int(start_dates[2]),
                            hour=0, minute=0, second=0)
    d_end_date = datetime(year=int(end_dates[0]), month=int(end_dates[1]), day=int(end_dates[2]),
                          hour=23, minute=59, second=59)
    list_date = db.get_users_stats(d_start_date, d_end_date, 0)
    if not list_date:
        await message.answer(
            "*Ошибка*: По данному периоду ничего не найдено, введите корректную дату",
            reply_markup=keyboard.back_menu,
            parse_mode='Markdown')
        return

    path = await generate_user_statistics(list_date, user_id, 0)
    graphic = FSInputFile(path)
    await bot.send_photo(chat_id=message.chat.id, photo=graphic, reply_markup=keyboard.manager_function_menu)
    await state.clear()
    await state.set_state(ManagerStates.manager)


@dp.message(F.text == "Назад", ManagerStates.manager)
@dp.message(F.text == "Назад", ManagerStates.manager_new_user)
@dp.message(F.text == "Назад", ManagerStates.manager_workload)
async def back_handler(message: Message, state: FSMContext) -> None:
    db.log_user_activity(message.from_user.id, message.message_id)
    await state.clear()
    await state.set_state(ManagerStates.manager)
    await message.reply("Вы вернулись в главное меню.", reply_markup=keyboard.manager_function_menu)


# Возвращение в главное меню для ReplyKeyboard
@dp.message(F.text == "Назад")
async def back_handler(message: Message, state: FSMContext) -> None:
    db.log_user_activity(message.from_user.id, message.message_id)
    await state.clear()
    main_menu = keyboard.create_main_menu(message.from_user.id)
    await message.reply("Вы вернулись в главное меню.", reply_markup=main_menu)


@dp.message(F.text == "Выход")
async def back_handler(message: Message, state: FSMContext) -> None:
    db.log_user_activity(message.from_user.id, message.message_id)
    await state.clear()
    await state.set_state(ManagerStates.manager)
    await message.reply("Вы вернулись в главное меню.", reply_markup=keyboard.manager_menu)


# Возвращение в главное меню для InlineKeyboard
@dp.callback_query(lambda c: c.data == "main_menu")
async def process_callback(callback_query: CallbackQuery) -> None:
    main_menu = keyboard.create_main_menu(callback_query.from_user.id)
    await callback_query.message.answer("Вы вернулись в главное меню.", reply_markup=main_menu)
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)


async def main() -> None:
    directories = [
        "../Photo/cut",
        "../Photo/noBg",
        "../Photo/original",
        "../Photo/ZIP/documents",
        "../Photo/statistic",
        "../Photo/PDF"
    ]

    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Создана папка: {directory}")
        else:
            print(f"Папка уже существует: {directory}")
    # Начало опроса обновлений
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
