import logging
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile
from numpy.compat import long

import config
import keyboard
from database.db import add_user, get_list_collection, get_all_images
from model.segment import Segmenter
from model.convert import Converter

executor = ThreadPoolExecutor()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.TOKEN)
# Инициализация диспетчера
dp = Dispatcher()

segmenter = Segmenter(model_path='../v3-965photo-100ep.pt')


# Состояния FSM
class States(StatesGroup):
    waiting_for_photo = State()  # Состояние ожидания фото для разметки
    function_photo = State() # Состояние ожидания функции
    change_collection_name = State() # Состояние ожидания ввода названия коллекции
    add_badge = State() # Состояние ожидания фото значка в модуле редактирования
    state_list = State()  # Состояние считывания сообщения с номером коллекции
    all_collection_create = State()


# Основные команды
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    # id и имя пользователя
    user_id: long = message.from_user.id
    user_full_name = message.from_user.full_name
    add_user(user_id)
    # Логируем взаимодействие с пользователем
    logging.info(f'{user_id=} {user_full_name=}')
    await message.answer(f"Привет, {user_full_name}! Я бот, для работы с коллекционными значками.",
                         reply_markup=keyboard.main_menu)


@dp.message(F.text == "Назад")
async def back_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.reply("Вы вернулись в главное меню.", reply_markup=keyboard.main_menu)


# Обработчики команд с фото
@dp.message(F.text == "Отправить фото")
async def send_photo_handler(message: Message, state: FSMContext) -> None:
    await message.answer("Пожалуйста, отправьте фото.", reply_markup=keyboard.function_menu)
    await state.set_state(States.waiting_for_photo)


@dp.message(F.photo, States.waiting_for_photo)
async def get_photo_handler(message: Message, state: FSMContext) -> None:
    # Скачивание оригинала
    photo_id = message.photo[-1]
    file_info = await bot.get_file(photo_id.file_id)
    image_path = f"../Photo/original/{photo_id.file_id}.jpg"
    await bot.download_file(file_path=file_info.file_path, destination=image_path)

    await message.answer("Фото получено.", reply_markup=keyboard.function_menu)
    await state.clear()
    await state.update_data(image_path=image_path, photo_id=photo_id.file_id)
    await state.set_state(States.function_photo)


@dp.message(F.text == "Посчитать количество", States.function_photo)
async def count_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    image_path = data.get('image_path')
    photo_id = data.get('photo_id')
    text_file_path, num_objects = segmenter.segment_image(image_path, photo_id)
    # Возвращаемся ли мы в основное меню (СНЯТЬ СТАТУС) или оставляем пользователя в этом (Ничего не делать)
    await message.answer(f"Количество найденных объектов на фотографии: {num_objects}",
                         reply_markup=keyboard.function_menu)


@dp.message(F.text == "Нарезать на отдельные значки", States.function_photo)
async def cut_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    image_path = data.get('image_path')
    photo_id = data.get('photo_id')
    loading_task = asyncio.create_task(send_loading_message(message.chat.id))
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(executor, segmenter.segment_image, image_path, photo_id)
    text_file_path, num_objects = result
    loading_task.cancel()
    for idx in range(num_objects):
        cropped_img_path = f"../Photo/noBg/{photo_id}_{idx}.png"
        photo_cropped = FSInputFile(cropped_img_path)
        await bot.send_photo(chat_id=message.chat.id, photo=photo_cropped)
    await state.update_data(num_objects=num_objects)
    await message.answer("Коллекция полная?", reply_markup=keyboard.yes_no_menu)

@dp.message(F.text == "Да")
async def yes_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(States.all_collection_create)
    await message.answer("Введите название коллекции.", reply_markup=keyboard.collection_menu)

@dp.message(F.text, States.all_collection_create)
async def create_collection_handler(message: Message, state: FSMContext) -> None:
    print(message.text)
    await message.reply("Секция 'Создания коллекции' пока в разработке.", reply_markup=keyboard.collection_menu)
    await state.clear()

@dp.message(F.text == "Нет")
async def no_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photo_id = data.get('photo_id')
    num_objects = data.get('num_objects')
    zip_file_path = f'../Photo/ZIP/{photo_id}.zip'
    converter = Converter()
    converter.convert_to_zip(photo_id, num_objects, zip_file_path)
    zip = FSInputFile(zip_file_path)
    await message.reply("В таком случае держите архив с размеченными значками.", reply_markup=keyboard.main_menu)
    await bot.send_document(chat_id=message.chat.id, document=zip)
    os.remove(zip_file_path)

# Обработчики команд с коллекциями
@dp.message(F.text == "Коллекции")
async def collections_handler(message: Message) -> None:
    await message.reply("Выберете в меню желаемое действие.", reply_markup=keyboard.collection_menu)


@dp.message(F.text == "Избранное")
async def favourites_handler(message: Message) -> None:
    await message.reply("Секция 'Избранное' пока в разработке.", reply_markup=keyboard.collection_menu)


@dp.message(F.text == "Весь список")
async def all_list_handler(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    await message.reply(
        "*Выберете номер коллекции для выгрузки в PDF*\n" + format_collection_list(get_list_collection(user_id)),
        reply_markup=keyboard.collection_menu, parse_mode='Markdown')
    await state.set_state(States.state_list)


@dp.message(F.text, States.state_list)
async def num_collection_handler(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    bd_message = get_list_collection(user_id)
    collection_id, name = (bd_message[int(message.text) - 1])
    images_list = get_all_images(collection_id)
    converter = Converter()
    pdf_path = converter.convert_to_pdf(name, collection_id, images_list)
    await state.clear()
    pdf = FSInputFile(pdf_path)
    await bot.send_document(chat_id=message.chat.id, document=pdf)


def format_collection_list(collections):
    if (collections == 'Нет коллекций'):
        return collections
    else:
        message = ""
        for i, (collection_id, name) in enumerate(collections, start=1):
            message += f"{i}. {name}\n"
        return message

      
@dp.message(F.text == "Добавить")
async def add_handler(message: Message) -> None:
    await message.reply("Секция 'Добавить' пока в разработке.", reply_markup=keyboard.collection_menu)


@dp.message(F.text == "Удалить")
async def remove_handler(message: Message) -> None:
    await message.reply("Секция 'Удалить' пока в разработке.", reply_markup=keyboard.collection_menu)


@dp.message(F.text == "Редактировать")
async def edit_handler(message: Message) -> None:
    await message.reply("Представим, что вы уже выбрали коллекцию из перечисленных. Что вы хотите сделать с данной коллекцией?", reply_markup=keyboard.edit_menu)

@dp.message(F.text == "Изменить название")
async def send_name_handler(message: Message, state: FSMContext) -> None:
    await message.reply("Просим вас ввести новое название для вашей коллекции.", reply_markup=keyboard.back_menu)
    await state.set_state(States.change_collection_name)

@dp.message(States.change_collection_name)
async def change_name_handler(message: Message) -> None:
    # if db.contains('collections_name', message):  # PS: Предполагаю такой метод в классе Database
    #     await message.reply("Такое название коллекции уже существует. Повторите попытку.", reply_markup=keyboard.back_menu)
    # else:
    #     db.update('collections_name', message) # PS: Предполагаю такой метод в классе Database
    #     await message.reply("Название коллекции успешно изменено.", reply_markup=keyboard.main_menu)
    pass

@dp.message(F.text == "Добавить значок")
async def send_badge_handler(message: Message, state: FSMContext) -> None:
    await message.reply("Пожалуйста, отправьте фото со значком, который вы хотите добавить в коллекцию.", reply_markup=keyboard.back_menu)
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
    await message.reply("Пожалуйста, отправьте фото со значком, который вы хотите добавить в коллекцию.", reply_markup=keyboard.back_menu)
    await state.set_state(States.add_badge)


@dp.message(F.text == "Инструкция")
async def instruction_handler(message: Message) -> None:
    instruction = (
        "*Рекомендации по улучшению качества нарезки:*\n"
        "1. Сделайте фотографию в высоком разрешении.\n"
        "2. Обеспечьте хорошее освещение.\n"
        "3. Используйте контрастный фон для фотографирования значков.\n"
        "4. Значки должны располагаться на достаточном расстоянии друг от друга"
        "*Ограничения:*\n"
        "1. Один пользователь может иметь не более 100 коллекций.\n"
        "2. Одна коллекция может содержать не более 200 фотографий."
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

async def main() -> None:
    # Начало опроса обновлений
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
