import logging
import asyncio

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
from database.db import Db
from model.segment import Segmenter
from model.convert import Converter

# Настройка логирования
logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.TOKEN)
# Инициализация диспетчера
dp = Dispatcher()

segmenter = Segmenter(model_path='../v3-965photo-100ep.pt')
db = Db()
# Состояния FSM
class States(StatesGroup):
    waiting_for_photo = State()  # Состояние ожидания фото
    function_photo = State()  # Состояние ожидания функции
    state_list = State()  # Состояние считывания сообщения с номером коллекции


# Основные команды
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    # id и имя пользователя
    user_id: long = message.from_user.id
    user_full_name = message.from_user.full_name
    db.add_user(user_id)
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
async def photo_handler(message: Message, state: FSMContext) -> None:
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
    # Отправка нарезанных изображений
    data = await state.get_data()
    image_path = data.get('image_path')
    photo_id = data.get('photo_id')
    text_file_path, num_objects = segmenter.segment_image(image_path, photo_id)
    # Временная функция отправки нарезанных значков без фона
    for idx in range(num_objects):
        cropped_img_path = f"../Photo/noBg/{photo_id}_{idx}.png"
        photo_cropped = FSInputFile(cropped_img_path)
        await bot.send_photo(chat_id=message.chat.id, photo=photo_cropped)
    await message.answer("Коллекция полная?", reply_markup=keyboard.yes_no_menu)


@dp.message(F.text == "Да")
async def yes_handler(message: Message) -> None:
    await message.reply("Секция 'Создания коллекции' пока в разработке.", reply_markup=keyboard.collection_menu)


@dp.message(F.text == "Нет")
async def no_handler(message: Message) -> None:
    await message.reply("Секция 'Отправки зип архивом' пока в разработке.", reply_markup=keyboard.collection_menu)


# Обработчики команд с коллекциями
@dp.message(F.text == "Коллекции")
async def collections_handler(message: Message) -> None:
    await message.reply("Выберете в меню желаемое действие.", reply_markup=keyboard.collection_menu)


@dp.message(F.text == "Избранное")
async def favourites_handler(message: Message) -> None:
    await message.reply("Секция 'Избранное' пока в разработке.", reply_markup=keyboard.collection_menu)


@dp.message(F.text == "Весь список")
async def collections_handler(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    await message.reply(
        "*Выберете номер коллекции для выгрузки в PDF*\n" + format_collection_list(db.get_list_collection(user_id)),
        reply_markup=keyboard.collection_menu, parse_mode='Markdown')
    await state.set_state(States.state_list)


@dp.message(F.text, States.state_list)
async def num_collection_handler(message: Message, state: FSMContext) -> None:
    #await message.reply("Я считал это " + message.text, reply_markup=keyboard.collection_menu)
    user_id = message.from_user.id
    bd_message = db.get_list_collection(user_id)
    collection_id, name = (bd_message[int(message.text) - 1])
    print(collection_id)
    print(name)
    images_list = db.get_all_images(collection_id)
    print(images_list)
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
async def collections_handler(message: Message) -> None:
    await message.reply("Секция 'Добавить' пока в разработке.", reply_markup=keyboard.collection_menu)


@dp.message(F.text == "Удалить")
async def collections_handler(message: Message) -> None:
    await message.reply("Секция 'Удалить' пока в разработке.", reply_markup=keyboard.collection_menu)


@dp.message(F.text == "Редактировать")
async def collections_handler(message: Message) -> None:
    await message.reply("Секция 'Весь список' пока в разработке.", reply_markup=keyboard.collection_menu)


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
async def tp_handler(message: Message) -> None:
    answer = (
        "Если у вас есть какие-то вопросы, вы можете обратиться к:\n\n"
        "@insignificance123\n"
        "@Mihter_2208\n"
        "@KatyaPark11\n"
        "@sech14"
    )
    await message.answer(answer, reply_markup=keyboard.main_menu),


async def main() -> None:
    # Начало опроса обновлений
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
