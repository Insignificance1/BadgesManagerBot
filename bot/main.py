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
from bot.settings.states import ManagerStates, CollectionStates, States
from bot.settings.keyboard import remove_keyboard, format_collection_list, format_collection_list_id, format_image_list
from services.other_service import get_collection_id_and_name
from services.task_manager import task_manager
from services.statistics_service import generate_user_statistics
from bot.settings.variables import bot, dp, db, executor

from handlers.image_handler import register_image_handlers
from handlers.instruction_handler import register_instruction_handlers
from handlers.photo_handler import register_photo_handlers
from handlers.collection_handler import register_collection_handlers

register_image_handlers(dp)
register_instruction_handlers(dp)
register_photo_handlers(dp)
register_collection_handlers(dp)


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
async def all_time_handler(message: Message, state: FSMContext) -> None:
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

    path = await generate_user_statistics(list_date, user_id)
    graphic = FSInputFile(path)
    await bot.send_photo(chat_id=message.chat.id, photo=graphic, reply_markup=keyboard.manager_function_menu)
    await state.clear()
    await state.set_state(ManagerStates.manager)


# Выбор действия над коллекциями
@dp.message(F.text == "Коллекции")
async def collections_handler(message: Message) -> None:
    db.log_user_activity(message.from_user.id, message.message_id)
    await message.reply("Выберите в меню желаемое действие.", reply_markup=keyboard.collections_menu)


# Выбор действия над избранными коллекциями
@dp.message(F.text == "Избранное")
async def favourites_list_handler(message: Message, state: FSMContext) -> None:
    db.log_user_activity(message.from_user.id, message.message_id)
    await message.answer('Выберите желаемое действие над избранными коллекциями.',
                         reply_markup=keyboard.favorite_collections_menu)
    await state.set_state(CollectionStates.favorites)


# Выбор избранной коллекции для выгрузки в PDF-файл
@dp.message(F.text == "Выгрузить в PDF", CollectionStates.favorites)
async def pdf_collections_handler(message: Message) -> None:
    db.log_user_activity(message.from_user.id, message.message_id)
    user_id = message.from_user.id
    await message.answer("*Выберите избранную коллекцию для выгрузки в PDF*\n",
                         reply_markup=await format_collection_list(db.get_list_favorites(user_id), 'pdf_favorite_'),
                         parse_mode='Markdown')


# Выбор избранной коллекции для смены названия
@dp.message(F.text == "Изменить название", CollectionStates.favorites)
async def send_name_handler(message: Message) -> None:
    db.log_user_activity(message.from_user.id, message.message_id)
    user_id = message.from_user.id
    await remove_keyboard(message)
    await message.answer("*Выберите избранную коллекцию для смены её названия*\n",
                         reply_markup=await format_collection_list(db.get_list_favorites(user_id), 'name_favorite_'),
                         parse_mode='Markdown')


# Просмотр избранной коллекции
@dp.message(F.text == "Посмотреть избранное")
async def show_handler(message: Message) -> None:
    db.log_user_activity(message.from_user.id, message.message_id)
    user_id = message.from_user.id
    await remove_keyboard(message)
    await message.reply(
        "*Выберите избранную коллекцию для её просмотра*\n", reply_markup=await format_collection_list(
            db.get_list_favorites(user_id), 'show_favorite_'), parse_mode='Markdown')


# Выбор коллекции для добавления в избранное
@dp.message(F.text == "Добавить в избранное")
async def add_favorites_list_handler(message: Message) -> None:
    db.log_user_activity(message.from_user.id, message.message_id)
    user_id = message.from_user.id
    await message.reply(
        "*Выберите коллекцию для добавления в избранное*\n", reply_markup=await format_collection_list(
            db.get_list_favorites(user_id, False), 'add_favorite_'), parse_mode='Markdown')
    await remove_keyboard(message)


# Выбор коллекции для удаления из избранного
@dp.message(F.text == "Удалить из избранного")
async def del_favorites_list_handler(message: Message) -> None:
    db.log_user_activity(message.from_user.id, message.message_id)
    user_id = message.from_user.id
    await message.reply(
        "*Выберите коллекцию для удаления из избранного*\n", reply_markup=await format_collection_list(
            db.get_list_favorites(user_id), "delete_favorite_"), parse_mode='Markdown')
    await remove_keyboard(message)


# Изменение флага избранности для выбранной коллекции
@dp.callback_query(lambda c: c.data.startswith("add_favorite_") or c.data.startswith("delete_favorite_"))
async def edit_favorite_handler(callback_query: CallbackQuery) -> None:
    db.log_user_activity(callback_query.from_user.id, callback_query.inline_message_id)
    # Запускаем параллельную задачу для режима ожидания
    task_manager.create_loading_task(callback_query.message.chat.id, f'task_{callback_query.from_user.id}')
    loop = asyncio.get_running_loop()
    # Получаем id и название коллекции
    is_favorite = callback_query.data.startswith("add_favorite_")
    type_id = 3 if is_favorite else 2
    collection_id, name = await get_collection_id_and_name(callback_query, loop, type_id)
    # Меняем флаг избранности
    await loop.run_in_executor(executor, db.edit_favorites, collection_id, is_favorite)
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    if is_favorite:
        await callback_query.message.answer(f"Коллекция {name} успешно добавлена в избранное.",
                                            reply_markup=keyboard.favorite_collections_menu)
    else:
        await callback_query.message.answer(f"Коллекция {name} удалена из избранного.",
                                            reply_markup=keyboard.favorite_collections_menu)
    task_manager.cancel_task_by_name(f'task_{callback_query.from_user.id}')


# Начало поиска коллекций и значков
@dp.message(F.text == "Поиск")
async def search_handler(message: Message, state: FSMContext) -> None:
    await message.answer("*Введите название коллекции или значка*",
                         reply_markup=keyboard.create_main_menu(message.from_user.id),
                         parse_mode='Markdown')
    await state.set_state(States.waiting_for_search)


@dp.message(F.text, States.waiting_for_search)
async def search(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    # Запускаем параллельную задачу для режима ожидания
    loading_task = asyncio.create_task(send_loading_message(message.chat.id))
    search_query = message.text
    await message.answer("*Результаты поиска\nКоллекции:\n*",
                         reply_markup=await format_collection_list_id(db.get_list_collection_for_name(user_id, search_query),
                                                                   'search_collection_'),
                         parse_mode='Markdown')
    loading_task.cancel()
    loading_task = asyncio.create_task(send_loading_message(message.chat.id))
    await message.answer("*Значки:\n*",
                         reply_markup=await format_image_list(db.get_all_images_for_name(user_id, search_query),
                                                                   'show_badge_'),
                         parse_mode='Markdown')
    loading_task.cancel()
    await state.clear()


# Режим ожидания
async def send_loading_message(chat_id):
    message = await bot.send_message(chat_id, "Ожидайте, бот думает")
    dots = ""
    try:
        while True:
            if dots == "...":
                dots = ""
            else:
                dots += "."
            await bot.edit_message_text(f"Ожидайте, бот думает{dots}", chat_id=chat_id, message_id=message.message_id)
            await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        await bot.delete_message(chat_id=chat_id, message_id=message.message_id)


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
