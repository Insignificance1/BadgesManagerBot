import logging
import asyncio
import os
import zipfile

from aiogram import types
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, \
    ReplyKeyboardRemove
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramBadRequest
from numpy.compat import long

import keyboard
from bot.settings.states import States
from model.convert import Converter
from model.segment import rotate_image
from keyboard import create_rotate_keyboard
from services.other_service import get_collection_id_and_name

from handlers.image_handler import register_image_handlers
from bot.settings.variables import bot, dp, segmenter, db, executor
register_image_handlers(dp)


# Настройка логирования
logging.basicConfig(level=logging.INFO)


# Знакомство с пользователем
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    # Добавляем пользователя в БД
    user_id: long = message.from_user.id
    user_full_name = message.from_user.full_name
    db.add_user(user_id)
    # Логируем взаимодействие с пользователем
    logging.info(f'{user_id=} {user_full_name=}')
    await message.answer(f"Привет, {user_full_name}! Я бот для работы с коллекционными значками.",
                         reply_markup=keyboard.main_menu)


# Ожидание отправки фото
@dp.message(F.text == "Отправить фото")
async def send_photo_handler(message: Message, state: FSMContext) -> None:
    await message.answer("Пожалуйста, отправьте фото.", reply_markup=keyboard.back_menu)
    await state.set_state(States.waiting_for_photo)


# Закачка полученного фото
@dp.message(F.photo, States.waiting_for_photo)
async def get_photo_handler(message: Message, state: FSMContext) -> None:
    # Скачиваем оригинал
    photo_id = message.photo[-1]
    file_info = await bot.get_file(photo_id.file_id)
    image_path = f"../Photo/original/{photo_id.file_id}.jpg"
    await bot.download_file(file_path=file_info.file_path, destination=image_path)

    await message.answer("Фото получено.", reply_markup=keyboard.function_menu)
    await state.clear()
    await state.update_data(image_path=image_path, photo_id=photo_id.file_id)
    await state.set_state(States.choose_function_photo)


# Подсчёт количества значков на фото
@dp.message(F.text == "Посчитать количество", States.choose_function_photo)
async def count_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    image_path = data.get('image_path')
    # Запускаем параллельную задачу для режима ожидания
    loading_task = asyncio.create_task(send_loading_message(message.chat.id))
    loop = asyncio.get_running_loop()
    num_objects = await loop.run_in_executor(executor, segmenter.get_count, image_path)
    # Даём пользователю возможность дальнейшей нарезки фото
    await message.answer(f"Количество найденных объектов на фотографии: {num_objects}",
                         reply_markup=keyboard.function_menu)
    # Завершаем режима ожидания
    loading_task.cancel()


# Нарезка фото на отдельные значки
@dp.message(F.text == "Нарезать на отдельные значки", States.choose_function_photo)
async def cut_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    image_path = data.get('image_path')
    photo_id = data.get('photo_id')
    await state.set_state(States.align_function_photo)
    # Запускаем параллельную задачу для режима ожидания
    loading_task = asyncio.create_task(send_loading_message(message.chat.id))
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(executor, segmenter.segment_image, image_path, photo_id)
    num_objects = result
    # Завершаем режима ожидания
    loading_task.cancel()
    # Выводим нарезанных фотографий
    for idx in range(num_objects):
        cropped_img_path = f"../Photo/noBg/{photo_id}_{idx}.png"
        photo_cropped = FSInputFile(cropped_img_path)
        await bot.send_photo(chat_id=message.chat.id, photo=photo_cropped, reply_markup=keyboard.align_menu)
    await state.update_data(image_path=image_path, photo_id=photo_id, num_objects=num_objects)


# Подготовка к выравниванию изображений
@dp.message(F.text == "Выровнять", States.align_function_photo)
async def edit_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photo_id = data.get('photo_id')
    num_objects = data.get('num_objects')
    idx = 0
    aligned_img_path = f"../Photo/noBg/{photo_id}_{idx}.png"
    # Создаём inline клавиатуры
    edit_keyboard = create_rotate_keyboard(idx, num_objects)
    photo_aligned = FSInputFile(aligned_img_path)

    await remove_keyboard(message)
    await bot.send_photo(chat_id=message.chat.id, photo=photo_aligned, reply_markup=edit_keyboard,
                         caption='ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ')
    await state.update_data(edit_idx=idx)


# Выравнивание изображений
@dp.callback_query(lambda c: c.data.startswith('rotate_'))
async def process_edit_callback(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photo_id = data.get('photo_id')
    edit_idx = data.get('edit_idx')
    num_objects = data.get('num_objects')
    action = callback_query.data.split('_')[-1]
    angle = 0

    if action == 'left':
        edit_idx = max(edit_idx - 1, 0)
    elif action == 'right':
        edit_idx += 1  # Увеличиваем idx для перехода к следующему изображению
    elif action == 'continue':
        await bot.send_message(chat_id=callback_query.message.chat.id, text="Коллекция полная?",
                               reply_markup=keyboard.yes_no_menu)
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await callback_query.answer()
        return
    elif action == 'exit':
        await bot.send_message(chat_id=callback_query.message.chat.id, text="Вы вернулись в главное меню.",
                               reply_markup=keyboard.main_menu)
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await callback_query.answer()
        return
    else:
        try:
            angle = int(action)
        except ValueError:
            raise ValueError("Обнаружено несуществующее действие")

    image_path = f"../Photo/noBg/{photo_id}_{edit_idx}.png"
    if angle != 0:
        rotate_image(image_path, angle)

    edit_keyboard = create_rotate_keyboard(edit_idx, num_objects)
    photo_aligned = FSInputFile(image_path)
    await bot.edit_message_media(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        media=types.InputMediaPhoto(media=photo_aligned,
                                    caption='ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ'),
        reply_markup=edit_keyboard
    )

    await state.update_data(edit_idx=edit_idx)
    await callback_query.answer()


# Продолжение после получения значков после нарезки
@dp.message(F.text == "Продолжить", States.align_function_photo)
async def continue_handler(message: Message) -> None:
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    await message.answer("Коллекция полная?", reply_markup=keyboard.yes_no_menu)


# Обработка для полной коллекции после нарезки
@dp.message(F.text == "Да")
async def yes_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(States.all_collection_create)
    await message.answer("Введите название коллекции.", reply_markup=keyboard.back_menu)


# Создание коллекции после нарезки
@dp.message(F.text, States.all_collection_create)
async def create_after_yes_handler(message: Message, state: FSMContext) -> None:
    # Запускаем параллельную задачу для режима ожидания
    loading_task = asyncio.create_task(send_loading_message(message.chat.id))
    data = await state.get_data()
    loop = asyncio.get_running_loop()
    try:
        # Добавляем коллекцию
        result = await loop.run_in_executor(executor, db.add_collection, message.from_user.id, message.text)
        reply, id_collection = result
        num_objects = data.get('num_objects')
        photo_id = data.get('photo_id')
        # Добавляем изображения в соответствующую коллекцию
        for idx in range(num_objects):
            img_path = f"../Photo/noBg/{photo_id}_{idx}.png"
            await loop.run_in_executor(executor, db.insert_image, message.from_user.id, img_path, id_collection)
        await message.reply(reply, reply_markup=keyboard.main_menu)
        # Завершаем режим ожидания
        loading_task.cancel()
    # Обрабатываем ошибки из других методов
    except Exception as e:
        await message.reply(str(e), reply_markup=keyboard.main_menu)
        await yes_handler(message, state)
        loading_task.cancel()
    await state.clear()


# Обработка для неполной коллекции после нарезки
@dp.message(F.text == "Нет")
async def no_handler(message: Message, state: FSMContext) -> None:
    # Создаём архив с параллельным режимом ожидания
    loading_task = asyncio.create_task(send_loading_message(message.chat.id))
    data = await state.get_data()
    photo_id = data.get('photo_id')
    num_objects = data.get('num_objects')
    zip_path = f'../Photo/ZIP/{photo_id}.zip'
    converter = Converter()
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(executor, converter.convert_to_zip, photo_id, num_objects, zip_path)
    # Отправляем архив
    zip_file = FSInputFile(zip_path)
    await message.reply("В таком случае держите архив с размеченными значками.", reply_markup=keyboard.main_menu)
    await bot.send_document(chat_id=message.chat.id, document=zip_file)
    # Завершаем режим ожидания
    loading_task.cancel()
    # Удаляем архив
    os.remove(zip_path)


# Выбор действия над коллекциями
@dp.message(F.text == "Коллекции")
async def collections_handler(message: Message) -> None:
    await message.reply("Выберите в меню желаемое действие.", reply_markup=keyboard.collections_menu)


# Выбор действия над списком коллекций
@dp.message(F.text == "Весь список")
async def all_list_handler(message: Message, state: FSMContext) -> None:
    await message.answer('Выберите желаемое действие над всем списком коллекций.',
                         reply_markup=keyboard.all_collections_menu)
    await state.set_state(States.collections)


# Вывод недостающих значки
@dp.message(F.text == "Вывести недостающие значки")
async def null_badges_list_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(States.state_null_badges)
    await pdf_collections_handler(message)


# Выбор действия над избранными коллекциями
@dp.message(F.text == "Избранное")
async def favourites_list_handler(message: Message, state: FSMContext) -> None:
    await message.answer('Выберите желаемое действие над избранными коллекциями.',
                         reply_markup=keyboard.favorite_collections_menu)
    await state.set_state(States.favorites)


# Выбор коллекции для выгрузки в PDF-файл
@dp.message(F.text == "Выгрузить в PDF", States.collections)
async def pdf_collections_handler(message: Message) -> None:
    user_id = message.from_user.id
    await message.answer("*Выберите коллекцию для выгрузки в PDF*\n",
                         reply_markup=await format_collection_list(db.get_list_collection(user_id), 'pdf_collection_'),
                         parse_mode='Markdown')


# Выбор избранной коллекции для выгрузки в PDF-файл
@dp.message(F.text == "Выгрузить в PDF", States.favorites)
async def pdf_collections_handler(message: Message) -> None:
    user_id = message.from_user.id
    await message.answer("*Выберите избранную коллекцию для выгрузки в PDF*\n",
                         reply_markup=await format_collection_list(db.get_list_favorites(user_id), 'pdf_favorite_'),
                         parse_mode='Markdown')


# Выбор коллекции для выгрузки в PDF-файл нулевых значков
@dp.message(F.text == "Выгрузить в PDF", States.state_null_badges)
async def pdf_collections_handler(message: Message) -> None:
    user_id = message.from_user.id
    await message.answer("*Выберите коллекцию для выгрузки в PDF*\n",
                         reply_markup=await format_collection_list(db.get_list_collection(user_id), 'pdf_null_'),
                         parse_mode='Markdown')


# Выгрузка в PDF-файл выбранной коллекции
@dp.callback_query(lambda c: c.data.startswith("pdf_collection_") or c.data.startswith("pdf_favorite_") or
                             c.data.startswith("pdf_null_"))
async def send_pdf(callback_query: CallbackQuery):
    # Запускаем параллельную задачу для режима ожидания
    loading_task = asyncio.create_task(send_loading_message(callback_query.message.chat.id))
    loop = asyncio.get_running_loop()
    # Получаем id и название коллекции
    type_id = 3
    if callback_query.data.startswith("pdf_null_"):
        type_id = 3
        null_or_all_images = db.get_null_badges
        is_all_count = False
    else:
        null_or_all_images = db.get_all_images
        is_all_count = True
        if callback_query.data.startswith("pdf_favorite_"):
            type_id = 2
        else:
            type_id = 1
    collection_id, name = await get_collection_id_and_name(callback_query, type_id=type_id)
    # Запрашиваем список путей всех изображений которых 0 или просто всех
    images_list = await loop.run_in_executor(executor, null_or_all_images, collection_id)
    count_list = await loop.run_in_executor(executor, db.get_list_count, collection_id, is_all_count)
    name_list = await loop.run_in_executor(executor, db.get_all_name, collection_id, is_all_count)
    converter = Converter()
    # Конвертируем изображения в один PDF-файл
    pdf_path = await loop.run_in_executor(executor, converter.convert_to_pdf_ext, name, collection_id,
                                          images_list, name_list, count_list)
    # Отправляем файл пользователю
    pdf = FSInputFile(pdf_path)
    loading_task.cancel()
    try:
        await bot.delete_message(chat_id=callback_query.message.chat.id,
                                 message_id=callback_query.message.message_id)
        await bot.send_document(chat_id=callback_query.message.chat.id, document=pdf, reply_markup=keyboard.back_menu)
        os.remove(pdf_path)
    except TelegramBadRequest:
        raise Exception("Что-то пошло не так. Вероятно, кнопка была нажата несколько раз.")


# Выбор коллекции для смены названия
@dp.message(F.text == "Изменить название", States.collections)
async def send_name_handler(message: Message) -> None:
    user_id = message.from_user.id
    await remove_keyboard(message)
    await message.answer("*Выберите коллекцию для смены её названия*\n",
                         reply_markup=await format_collection_list(db.get_list_collection(user_id), 'name_collection_'),
                         parse_mode='Markdown')


# Выбор избранной коллекции для смены названия
@dp.message(F.text == "Изменить название", States.favorites)
async def send_name_handler(message: Message) -> None:
    user_id = message.from_user.id
    await remove_keyboard(message)
    await message.answer("*Выберите избранную коллекцию для смены её названия*\n",
                         reply_markup=await format_collection_list(db.get_list_favorites(user_id), 'name_favorite_'),
                         parse_mode='Markdown')


# Ожидание ввода названия коллекции
@dp.callback_query(lambda c: c.data.startswith("name_collection_") or c.data.startswith("name_favorite_"))
async def change_name_handler(callback_query: CallbackQuery, state: FSMContext) -> None:
    type_id = 2 if callback_query.data.startswith("name_favorite_") else 1
    collection_id, name = await get_collection_id_and_name(callback_query, type_id=type_id)
    await callback_query.message.answer("Просим вас ввести новое название для коллекции",
                                        reply_markup=keyboard.back_menu)
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await state.update_data(collection_id=collection_id)
    new_state = States.waiting_for_name_collection if type_id == 1 else States.waiting_for_name_favorite
    await state.set_state(new_state)


# Смена названия коллекции
@dp.message(F.text, States.waiting_for_name_collection)
@dp.message(F.text, States.waiting_for_name_favorite)
async def new_name_handler(message: Message, state: FSMContext) -> None:
    # Запускаем параллельную задачу для режима ожидания
    loading_task = asyncio.create_task(send_loading_message(message.chat.id))
    loop = asyncio.get_running_loop()
    new_name = message.text
    data = await state.get_data()
    collection_id = data['collection_id']
    user_id = message.from_user.id
    try:
        # Обновляем название коллекции
        reply = await loop.run_in_executor(executor, db.update_collection_name, user_id, new_name, collection_id)
        await message.reply(reply, reply_markup=keyboard.collections_menu)
    # Обрабатываем ошибки
    except Exception as e:
        if States.waiting_for_name_collection:
            await state.set_state(States.collections)
        else:
            await state.set_state(States.favorites)
        await send_name_handler(message)
        await message.answer(str(e))
        loading_task.cancel()
    await state.clear()
    # Завершаем режим ожидания
    loading_task.cancel()


# Просмотр коллекции
@dp.message(F.text == "Посмотреть коллекцию")
async def show_handler(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    await remove_keyboard(message)
    await message.reply(
        "*Выберите коллекцию для её просмотра*\n", reply_markup=await format_collection_list(
            db.get_list_collection(user_id), 'show_collection_'), parse_mode='Markdown')
    await state.update_data(edit_idx=0)


# Просмотр избранной коллекции
@dp.message(F.text == "Посмотреть избранное")
async def show_handler(message: Message) -> None:
    user_id = message.from_user.id
    await remove_keyboard(message)
    await message.reply(
        "*Выберите избранную коллекцию для её просмотра*\n", reply_markup=await format_collection_list(
            db.get_list_favorites(user_id), 'show_favorite_'), parse_mode='Markdown')


# Выбор коллекции для добавления в избранное
@dp.message(F.text == "Добавить в избранное")
async def add_favorites_list_handler(message: Message) -> None:
    user_id = message.from_user.id
    await message.reply(
        "*Выберите коллекцию для добавления в избранное*\n", reply_markup=await format_collection_list(
            db.get_list_favorites(user_id, False), 'add_favorite_'), parse_mode='Markdown')
    await remove_keyboard(message)


# Выбор коллекции для удаления из избранного
@dp.message(F.text == "Удалить из избранного")
async def del_favorites_list_handler(message: Message) -> None:
    user_id = message.from_user.id
    await message.reply(
        "*Выберите коллекцию для удаления из избранного*\n", reply_markup=await format_collection_list(
            db.get_list_favorites(user_id), "delete_favorite_"), parse_mode='Markdown')
    await remove_keyboard(message)


# Изменение флага избранности для выбранной коллекции
@dp.callback_query(lambda c: c.data.startswith("add_favorite_") or c.data.startswith("delete_favorite_"))
async def edit_favorite_handler(callback_query: CallbackQuery) -> None:
    # Запускаем параллельную задачу для режима ожидания
    loading_task = asyncio.create_task(send_loading_message(callback_query.message.chat.id))
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
    loading_task.cancel()


# Выбор коллекции для пополнения
@dp.message(F.text == "Пополнить коллекцию")
async def add_handler(message: Message) -> None:
    user_id = message.from_user.id
    await message.reply(
        "*Выберите коллекцию для её пополнения*\n", reply_markup=await format_collection_list(
            db.get_list_collection(user_id), 'add_badges_'), parse_mode='Markdown')
    await remove_keyboard(message)


# Ожидание архива с изображениями для пополнения коллекции
@dp.callback_query(lambda c: c.data.startswith("add_badges_"))
async def add_badges_handler(callback_query: CallbackQuery, state: FSMContext) -> None:
    collection_id, name = await get_collection_id_and_name(callback_query, type_id=1)
    await callback_query.message.answer("Отправьте ZIP-файл с изображениями.", reply_markup=keyboard.back_menu)
    await state.update_data(collection_id=collection_id, collection_name=name)
    await state.set_state(States.waiting_for_zip_add)
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)


# Пополнение коллекции
@dp.message(F.document, States.waiting_for_zip_add)
async def get_zip_handler(message: Message, state: FSMContext) -> None:
    await message.reply("Файл получен.", reply_markup=keyboard.back_menu)
    # Запускаем параллельную задачу для режима ожидания
    loading_task = asyncio.create_task(send_loading_message(message.chat.id))
    data = await state.get_data()
    collection_id = data.get('collection_id')
    collection_name = data.get('collection_name')
    zip_file_id = message.document.file_id

    try:
        await process_zip_file(
            zip_file_id=zip_file_id,
            collection_id=collection_id,
            user_id=message.from_user.id,
            reply_func=lambda: message.reply(f"Коллекция '{collection_name}' успешно пополнена.",
                                             reply_markup=keyboard.main_menu)
        )
        # Завершаем режим ожидания
        loading_task.cancel()
    except Exception as e:
        await message.reply(f"Ошибка при пополнении коллекции: {e}", reply_markup=keyboard.main_menu)
        loading_task.cancel()

    await state.clear()


# Ожидание архива с изображениями при создании коллекции
@dp.message(F.text == "Добавить коллекцию")
async def add_handler(message: Message, state: FSMContext) -> None:
    await message.reply("Отправьте ZIP-файл с изображениями.", reply_markup=keyboard.back_menu)
    await state.set_state(States.waiting_for_zip_create)


# Ожидание ввода названия новой коллекции
@dp.message(F.document, States.waiting_for_zip_create)
async def get_zip_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(zip_file_id=message.document.file_id)
    await message.reply("Файл получен. Введите название новой коллекции.", reply_markup=keyboard.back_menu)
    await state.set_state(States.add_new_collection_zip_name)


# Создание коллекции
@dp.message(F.text, States.add_new_collection_zip_name)
async def create_collection_handler(message: Message, state: FSMContext) -> None:
    # Запускаем параллельную задачу для режима ожидания
    loading_task = asyncio.create_task(send_loading_message(message.chat.id))
    data = await state.get_data()
    zip_file_id = data.get('zip_file_id')

    # Добавляем коллекцию
    while True:
        collection_name = message.text
        try:
            collection_id = db.add_collection(message.from_user.id, collection_name)[1]
            break
        except Exception as e:
            await message.reply(str(e) + '\nПопробуйте ещё раз.', reply_markup=keyboard.back_menu)
            loading_task.cancel()
            collection_name = await dp.throttle("collection_name", rate=1)(
                dp.message(F.text, States.add_new_collection_zip_name))
            continue

    try:
        await process_zip_file(
            zip_file_id=zip_file_id,
            collection_id=collection_id,
            user_id=message.from_user.id,
            reply_func=lambda: message.reply(f"Коллекция '{collection_name}' успешно создана.",
                                             reply_markup=keyboard.main_menu)
        )
        # Завершаем режим ожидания
        loading_task.cancel()
    except Exception as e:
        await message.reply(f"Ошибка при создании коллекции: {e}", reply_markup=keyboard.main_menu)
        loading_task.cancel()

    await state.clear()


# Обработка архива
async def process_zip_file(zip_file_id, collection_id, user_id, reply_func):
    loop = asyncio.get_running_loop()

    # Загружаем архив
    zip_file = await bot.get_file(zip_file_id)
    zip_path = f'../Photo/ZIP/{zip_file.file_path}'
    await bot.download_file(zip_file.file_path, zip_path)

    zip_ref = zipfile.ZipFile(zip_path, 'r')
    images = []
    # Добавляем изображения в папку
    for idx, file in enumerate(zip_ref.namelist()):
        filename, file_extension = os.path.splitext(file)
        if file_extension == '.png' or file_extension == '.jpeg':
            new_filename = f"{zip_file_id}_{idx}{file_extension}"
            zip_ref.extract(file, '../Photo/noBg/')
            os.rename(f"../Photo/noBg/{file}", f"../Photo/noBg/{new_filename}")
            images.append(new_filename)

    zip_ref.close()
    os.remove(zip_path)

    # Добавляем изображения в БД
    for img_name in images:
        img_path = f"../Photo/noBg/{img_name}"
        await loop.run_in_executor(executor, db.insert_image, user_id, img_path, collection_id)

    await reply_func()


# Выбор коллекции для удаления
@dp.message(F.text == "Удалить коллекцию")
async def delete_collection_handler(message: Message) -> None:
    user_id = message.from_user.id
    await message.answer("*Выберите коллекцию для её удаления*\n",
                         reply_markup=await format_collection_list(db.get_list_collection(user_id),
                                                                   'delete_collection_'),
                         parse_mode='Markdown')


# Удаление коллекции
@dp.callback_query(lambda c: c.data.startswith("delete_collection_"))
async def delete_collection_number_handler(callback_query: CallbackQuery) -> None:
    # Запускаем параллельную задачу для режима ожидания
    loading_task = asyncio.create_task(send_loading_message(callback_query.message.chat.id))
    loop = asyncio.get_running_loop()
    # Получаем id коллекции
    collection_id = (await get_collection_id_and_name(callback_query, loop, 1))[0]
    await loop.run_in_executor(executor, db.delete_collection, callback_query.from_user.id, collection_id)
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await callback_query.message.answer("Коллекция успешно удалена.", reply_markup=keyboard.collections_menu)
    # Завершаем режим ожидания
    loading_task.cancel()


# Форматирование списка коллекций в InlineKeyboard
async def format_collection_list(collections, prefix):
    new_keyboard = []
    if collections not in ['Нет коллекций', 'Нет избранных коллекций']:
        for i, (_, name) in enumerate(collections, start=1):
            button_text = f"{i}. {name}"
            callback_data = f"{prefix}{i}"
            new_keyboard.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
    new_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=new_keyboard)


# Вывод инструкции
@dp.message(F.text == "Инструкция")
async def instruction_handler(message: Message) -> None:
    instruction = (
        "*Рекомендации по улучшению качества нарезки:*\n"
        "1. Сделайте фотографию в высоком разрешении.\n"
        "2. Обеспечьте хорошее освещение.\n"
        "3. Используйте контрастный фон для фотографирования значков.\n"
        "4. Значки должны располагаться на достаточном расстоянии друг от друга.\n\n"
        "*Ограничения:*\n"
        "1. Один пользователь может иметь не более 100 коллекций.\n"
        "2. Одна коллекция может содержать не более 200 фотографий.\n"
        "3. Название коллекции должно содержать от 3 до 55 символов.\n"
        "4. Название значка должно содержать от 3 до 30 символов."
    )
    await message.answer(instruction, reply_markup=keyboard.instruction_menu, parse_mode='Markdown')


# Обращение к ТП
@dp.message(F.text == "Обратиться к ТП")
async def support_handler(message: Message) -> None:
    answer = (
        "Если у вас есть какие-то вопросы, вы можете обратиться к:\n\n"
        "@insignificance123\n"
        "@Mihter_2208\n"
        "@KatyaPark11\n"
        "@sech14"
    )
    await message.answer(answer, reply_markup=keyboard.main_menu),


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


# Удаление клавиатуры
async def remove_keyboard(message: Message) -> None:
    await message.answer("ㅤ", reply_markup=ReplyKeyboardRemove())
    await bot.delete_message(message.chat.id, message.message_id + 1)


# Возвращение в главное меню для ReplyKeyboard
@dp.message(F.text == "Назад")
async def back_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.reply("Вы вернулись в главное меню.", reply_markup=keyboard.main_menu)


# Возвращение в главное меню для InlineKeyboard
@dp.callback_query(lambda c: c.data == "main_menu")
async def process_callback(callback_query: CallbackQuery) -> None:
    await callback_query.message.answer("Вы вернулись в главное меню.", reply_markup=keyboard.main_menu)
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)


async def main() -> None:
    # Начало опроса обновлений
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
