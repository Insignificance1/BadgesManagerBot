import logging
import asyncio
import os
import zipfile
from concurrent.futures import ThreadPoolExecutor

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, CallbackQuery
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from numpy.compat import long

import config
from bot import keyboard
from database.db import Db

from model.segment import Segmenter
from model.convert import Converter

executor = ThreadPoolExecutor()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.TOKEN)
# Инициализация диспетчера
dp = Dispatcher()

segmenter = Segmenter(model_path='../v3-965photo-100ep.pt')
db = Db()


# Состояния FSM
class States(StatesGroup):
    waiting_for_zip = State()  # Состояние ожидания ZIP-файла
    waiting_for_photo = State()                 # Ожидание фото для разметки
    choose_function_photo = State()             # Ожидание выбора функции обработки фото
    change_collection_name = State()            # Ожидание ввода названия коллекции
    add_new_collection_zip_name = State()       # Ожидание создание новой колекции из ZIP файла с именем
    add_badge = State()                         # Ожидание фото значка в модуле редактирования
    collections = State()
    favorites = State()
    state_list = State()                        # Состояние считывания сообщения с номером коллекции
    state_favorite_list = State()               # Состояние считывания сообщения с номером избранной коллекции
    state_add_favorite_list = State()           # Состояние считывания сообщения с номером коллекции для добавления в избранное
    state_del_favorite_list = State()           # Состояние считывания сообщения с номером коллекции для удаления из избранного
    change_favorite_collection_name = State()   # Состояние ожидания ввода названия избранной коллекции
    waiting_for_new_name = State()              # Ожидает задания имени
    state_back = State()                        # Ждёт кнопки назад
    state_del_collection = State()              # Состояние ожидания удаления коллекции
    all_collection_create = State()


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
        await bot.send_photo(chat_id=message.chat.id, photo=photo_cropped)
    await state.update_data(num_objects=num_objects)
    await message.answer("Коллекция полная?", reply_markup=keyboard.yes_no_menu)

# Обработка для полной коллекции после нарезки
@dp.message(F.text == "Да")
async def yes_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(States.all_collection_create)
    await message.answer("Введите название коллекции.", reply_markup=keyboard.back_menu)

# Создание коллекции после нарезки
@dp.message(F.text, States.all_collection_create)
async def create_collection_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    loop = asyncio.get_running_loop()
    try:
        # Добавляем коллекцию с параллельным режимом ожидания
        loading_task = asyncio.create_task(send_loading_message(message.chat.id))
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
                         reply_markup=format_collection_list(db.get_list_collection(user_id), 'pdf_collection_'),
                         parse_mode='Markdown')

# Выбор избранной коллекции для выгрузки в PDF-файл
@dp.message(F.text == "Выгрузить в PDF", States.favorites)
async def pdf_collections_handler(message: Message) -> None:
    user_id = message.from_user.id
    await message.answer("*Выберите избранную коллекцию для выгрузки в PDF*\n",
                         reply_markup=format_collection_list(db.get_list_favorites(user_id), 'pdf_favorite_'),
                         parse_mode='Markdown')

# Выгрузка в PDF-файл выбранной коллекции
@dp.callback_query(lambda c: c.data.startswith("pdf_collection_") or c.data.startswith("pdf_favorite_"))
async def send_pdf(callback_query: CallbackQuery):
    # Запускаем параллельную задачу для режима ожидания
    loading_task = asyncio.create_task(send_loading_message(callback_query.message.chat.id))
    loop = asyncio.get_running_loop()
    # Получаем id и название коллекции
    collection_id, name = await get_collection_id_and_name(callback_query, 'pdf_collection_', loop)
    # Запрашиваем список путей всех изображений
    images_list = await loop.run_in_executor(executor, db.get_all_images, collection_id)
    converter = Converter()
    # Конвертируем изображения в один PDF-файл
    pdf_path = await loop.run_in_executor(executor, converter.convert_to_pdf, name, collection_id, images_list)
    # Отправляем файл пользователю
    pdf = FSInputFile(pdf_path)
    loading_task.cancel()
    try:
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await bot.send_document(chat_id=callback_query.message.chat.id, document=pdf)
    except TelegramBadRequest:
        raise Exception("Что-то пошло не так. Вероятно, кнопка была нажата несколько раз.")

# Выбор коллекции для смены названия
@dp.message(F.text == "Изменить название", States.collections)
async def send_name_handler(message: Message) -> None:
    user_id = message.from_user.id
    await message.answer("*Выберите коллекцию для смены её названия*\n",
                         reply_markup=format_collection_list(db.get_list_collection(user_id), 'name_collection_'),
                         parse_mode='Markdown')

# Выбор избранной коллекции для смены названия
@dp.message(F.text == "Изменить название", States.favorites)
async def send_name_handler(message: Message) -> None:
    user_id = message.from_user.id
    await message.answer("*Выберите избранную коллекцию для смены её названия*\n",
                         reply_markup=format_collection_list(db.get_list_favorites(user_id), 'name_favorite_'),
                         parse_mode='Markdown')

# Ожидание ввода названия коллекции
@dp.callback_query(lambda c: c.data.startswith("name_collection_") or c.data.startswith("name_favorite_"))
async def change_name_handler(callback_query: CallbackQuery, state: FSMContext) -> None:
    collection_id, name = await get_collection_id_and_name(callback_query, 'name_collection_')
    await callback_query.message.reply("Просим вас ввести новое название для коллекции",
                                       reply_markup=keyboard.back_menu)
    await state.update_data(collection_id=collection_id)
    await state.set_state(States.waiting_for_new_name)

# Смена названия коллекции
@dp.message(F.text, States.waiting_for_new_name)
async def new_name_handler(message: Message, state: FSMContext) -> None:
    loading_task = asyncio.create_task(send_loading_message(message.chat.id))
    loop = asyncio.get_running_loop()
    new_name = message.text
    data = await state.get_data()
    collection_id = data['collection_id']
    user_id = message.from_user.id
    result = await loop.run_in_executor(executor, db.contains_collection_name, user_id, new_name)
    if result > 0:
        await message.reply("Такое название коллекции уже существует. Повторите попытку.",
                            reply_markup=keyboard.back_menu)
    else:
        await loop.run_in_executor(executor, db.update_name_collection, new_name, collection_id)
        await message.reply("Название коллекции успешно изменено.", reply_markup=keyboard.main_menu)
        await state.clear()
        loading_task.cancel()

@dp.message(F.text == "Добавить в избранное")
async def add_favourites_list_handler(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    await message.reply(
        "*Выберите коллекцию для добавления в избранное*\n", reply_markup=format_collection_list(
            db.get_list_favorites(user_id), 'add_favorite_'))

@dp.message(F.text == "Удалить из избранного")
async def del_favourites_list_handler(message: Message) -> None:
    user_id = message.from_user.id
    await message.reply(
        "*Ваш список избранного\nВведите номер коллекции которую желаете удалить из избранного*\n", reply_markup=format_collection_list(
            db.get_list_favorites(user_id), 'delete_favorite_'))

@dp.callback_query(lambda c: c.data.startswith("add_favorite_") or c.data.startswith("delete_favorite_"))
async def edit_favorite_handler(message: Message, state: FSMContext) -> None:
    loading_task = asyncio.create_task(send_loading_message(message.chat.id))
    user_id = message.from_user.id
    loop = asyncio.get_running_loop()
    if await state.get_state() == States.state_add_favorite_list.state:
        bd_message = await loop.run_in_executor(executor, db.get_list_collection, user_id)
        is_favorite = True
    else:
        bd_message = await loop.run_in_executor(executor, db.get_list_favorites, user_id)
        is_favorite = False
    try:
        collection_id, name = bd_message[int(message.text) - 1]
    except Exception:
        await message.reply("Введите корректный номер коллекции в пределах списка.")
        loading_task.cancel()
        await favourites_list_handler(message, state)
        return
    await loop.run_in_executor(executor, db.edit_favorites, collection_id, is_favorite)
    await state.clear()
    await message.answer(f"*Действия для {name} выполнены*\n" + format_collection_list(db.get_list_favorites(user_id)),
                         reply_markup=keyboard.favorite_collections_menu, parse_mode='Markdown')
    loading_task.cancel()


# Форматирование списка коллекций
def format_collection_list(collections, prefix):
    new_keyboard = []
    if collections not in ['Нет коллекций', 'Нет избранных коллекций']:
        for i, (_, name) in enumerate(collections, start=1):
            button_text = f"{i}. {name}"
            callback_data = f"{prefix}{i}"
            new_keyboard.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
    new_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=new_keyboard)

@dp.message(F.text == "Добавить коллекцию")
async def add_handler(message: Message, state: FSMContext) -> None:
    await message.reply("Отправьте ZIP-файл с изображениями.", reply_markup=keyboard.back_menu)
    await state.set_state(States.waiting_for_zip)


@dp.message(F.document, States.waiting_for_zip)
async def get_zip_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(zip_file_id=message.document.file_id)
    await message.reply("Файл получен. Введите название новой коллекции.", reply_markup=keyboard.back_menu)
    await state.set_state(States.add_new_collection_zip_name)


@dp.message(F.text, States.add_new_collection_zip_name)
async def create_collection_handler(message: Message, state: FSMContext) -> None:
    loading_task = asyncio.create_task(send_loading_message(message.chat.id))
    loop = asyncio.get_running_loop()
    data = await state.get_data()
    zip_file_id = data.get('zip_file_id')
    collection_name = message.text
    collection_id = 0

    while True:
        collection_name = message.text
        try:
            collection_id = db.add_collection(message.from_user.id, collection_name)
            break
        except Exception as e:
            await message.reply("Коллекция с таким именем уже существует. Введите новое имя:", reply_markup=keyboard.back_menu)
            loading_task.cancel()
            collection_name = await dp.throttle("collection_name", rate=1)(dp.message(F.text, States.add_new_collection_zip_name))
            continue

    try:
        zip_file = await bot.get_file(zip_file_id)
        zip_path = f'../Photo/ZIP/{zip_file.file_path}'
        await bot.download_file(zip_file.file_path, zip_path)

        zip_ref = zipfile.ZipFile(zip_path, 'r')
        images = []
        for idx, file in enumerate(zip_ref.namelist()):
            filename, file_extension = os.path.splitext(file)
            if file_extension == '.png':
                new_filename = f"{zip_file_id}_{idx}.png"
                zip_ref.extract(file, '../Photo/noBg/')
                os.rename(f"../Photo/noBg/{file}", f"../Photo/noBg/{new_filename}")
                images.append(new_filename)

        zip_ref.close()
        os.remove(zip_path)

        for img_name in images:
            img_path = f"../Photo/noBg/{img_name}"
            await loop.run_in_executor(executor, db.insert_image, message.from_user.id, img_path, collection_id[1])

        await message.reply(f"Коллекция '{collection_name}' успешно создана.", reply_markup=keyboard.main_menu)
        loading_task.cancel()
    except Exception as e:
        await message.reply(f"Ошибка при создании коллекции: {e}", reply_markup=keyboard.main_menu)
        loading_task.cancel()

    await state.clear()


@dp.message(F.text == "Удалить коллекцию")
async def delete_collection_handler(message: Message, state: FSMContext) -> None:
    loop = asyncio.get_running_loop()
    user_id = message.from_user.id
    collections = await loop.run_in_executor(executor, db.get_list_collection, user_id)
    if len(collections) == 0:
        await message.reply("У вас нет коллекций.", reply_markup=keyboard.collections_menu)
    else:
        collection_list = "Выберите коллекцию для удаления:\n"
        for i, collection in enumerate(collections, start=1):
            collection_list += f"{i}. {collection[1]}\n"
        await message.reply(collection_list, reply_markup=keyboard.back_menu)
        await state.set_state(States.state_del_collection)


@dp.message(F.text, States.state_del_collection)
async def delete_collection_number_handler(message: Message, state: FSMContext) -> None:
    loop = asyncio.get_running_loop()
    data = await state.get_data()
    user_id = message.from_user.id
    try:
        collection_number = int(message.text)
    except ValueError:
        await message.reply("Неверный формат номера коллекции. Попробуйте ещё раз.", reply_markup=keyboard.back_menu)
        return

    collections = await loop.run_in_executor(executor, db.get_list_collection, user_id)
    if 0 < collection_number <= len(collections):
        collection_id = collections[collection_number - 1][0]
        await loop.run_in_executor(executor, db.delete_collection,user_id, collection_id)
        await message.reply("Коллекция успешно удалена.", reply_markup=keyboard.collections_menu)
    else:
        await message.reply("Неверный номер коллекции. Попробуйте ещё раз.", reply_markup=keyboard.back_menu)

    await state.clear()


@dp.message(F.text == "Редактировать")
async def edit_handler(message: Message) -> None:
    await message.reply(
        "Представим, что вы уже выбрали коллекцию из перечисленных. Что вы хотите сделать с данной коллекцией?",
        reply_markup=keyboard.all_collections_menu)


@dp.message(F.text == "Добавить значок")
async def send_badge_handler(message: Message, state: FSMContext) -> None:
    await message.reply("Пожалуйста, отправьте фото со значком, который вы хотите добавить в коллекцию.",
                        reply_markup=keyboard.back_menu)
    await state.set_state(States.add_badge)


@dp.message(F.photo, States.add_badge)
async def add_badge_handler(message: Message, state: FSMContext) -> None:
    # # Получение файла фотографии
    # photo = message.photo[-1]  # Берем последнюю (самую крупную) версию фотографии
    # file_info = await bot.get_file(photo.file_id)
    # file = await bot.download_file(file_info.file_path)
    #
    # # Преобразование файла в байтовый поток
    # bytes_stream = BytesIO()
    # bytes_stream.write(file.read())
    # bytes_stream.seek(0)
    #
    # try:
    #     conn = get_db_connection()
    #     cursor = conn.cursor()
    #
    #     # Запись фотографии в базу данных
    #     cursor.execute("INSERT INTO photos (user_id, photo) VALUES (%s, %s)",
    #                    (message.from_user.id, psycopg2.Binary(bytes_stream.getvalue())))
    #     conn.commit()
    #
    #     cursor.close()
    #     conn.close()
    #
    #     await message.reply("Фотография успешно добавлена в базу данных!")
    # except Exception as e:
    #     logging.error(f"Ошибка при добавлении фотографии в базу данных: {e}")
    #     await message.reply("Произошла ошибка при добавлении фотографии в базу данных.")
    pass


@dp.message(F.text == "Удалить значок")
async def send_name_handler(message: Message, state: FSMContext) -> None:
    await message.reply("Пожалуйста, отправьте фото со значком, который вы хотите добавить в коллекцию.",
                        reply_markup=keyboard.back_menu)
    await state.set_state(States.add_badge)

async def get_collection_id_and_name(callback_query, col_prefix='', loop=None):
    if loop is None:
        loop = asyncio.get_running_loop()
    user_id = callback_query.from_user.id
    # Ищем id коллекции и её название в БД
    if col_prefix != '' or callback_query.data.startswith(col_prefix):
        db_message = await loop.run_in_executor(executor, db.get_list_collection, user_id)
    else:
        db_message = await loop.run_in_executor(executor, db.get_list_favorites, user_id)
    collection_id, name = db_message[int(callback_query.data.split("_")[2]) - 1]
    return collection_id, name

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
        "3. Название коллекции должно содержать от 3 до 100 символов.\n"
        "4. Название значка должно содержать от 3 до 70 символов."
    )
    await message.answer(instruction, reply_markup=keyboard.instruction_menu, parse_mode='Markdown')


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

# Возвращение в главное меню
@dp.message(F.text == "Назад")
async def back_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.reply("Вы вернулись в главное меню.", reply_markup=keyboard.main_menu)

@dp.callback_query(lambda c: c.data == "main_menu")
async def process_callback(callback_query: CallbackQuery):
    await callback_query.message.answer("Вы вернулись в главное меню.", reply_markup=keyboard.main_menu)
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)

async def main() -> None:
    # Начало опроса обновлений
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
