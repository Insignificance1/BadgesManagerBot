import logging
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile

import config
import keyboard
from model.segment import segment_image

# Настройка логирования
logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.TOKEN)
# Инициализация диспетчера
dp = Dispatcher()

# Состояния FSM
class States(StatesGroup):
    waiting_for_photo = State()  # Состояние ожидания фото для разметки
    function_photo = State() # Состояние ожидания функции
    change_collection_name = State() # Состояние ожидания ввода названия коллекции
    add_badge = State() # Состояние ожидания фото значка в модуле редактирования

# Основные команды
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    # id и имя пользователя
    user_id = message.from_user.id
    user_full_name = message.from_user.full_name
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
    downloaded_file = await bot.download_file(file_info.file_path, image_path)

    await message.answer("Фото получено.", reply_markup=keyboard.function_menu)
    await state.clear()
    await state.update_data(image_path=image_path, photo_id=photo_id.file_id)
    await state.set_state(States.function_photo)

@dp.message(F.text == "Посчитать количество", States.function_photo)
async def count_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    image_path = data.get('image_path')
    photo_id = data.get('photo_id')
    text_file_path, num_objects = segment_image(image_path, photo_id)
    # Возвращаемся ли мы в основное меню (СНЯТЬ СТАТУС) или оставляем пользователя в этом (Ничего не делать)
    await message.answer(f"Количество найденных объектов на фотографии: {num_objects}", reply_markup=keyboard.function_menu)

@dp.message(F.text == "Нарезать на отдельные значки", States.function_photo)
async def cut_handler(message: Message, state: FSMContext) -> None:
    # Отправка нарезанных изображений
    #await bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id)
    data = await state.get_data()
    image_path = data.get('image_path')
    photo_id = data.get('photo_id')
    text_file_path, num_objects = segment_image(image_path, photo_id)
    user_id = message.from_user.id
    #Временная функция отправки нарезанных значков без фона
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
    await message.reply("Секция 'Коллекции' пока в разработке.", reply_markup=keyboard.collection_menu)
    
@dp.message(F.text == "Избранное")
async def favourites_handler(message: Message) -> None:
    await message.reply("Секция 'Избранное' пока в разработке.", reply_markup=keyboard.collection_menu)
    
@dp.message(F.text == "Весь список")
async def all_list_handler(message: Message) -> None:
    await message.reply("Секция 'Весь список' пока в разработке.", reply_markup=keyboard.collection_menu)

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
    await message.reply("Здесь будет инструкция по использованию бота.", reply_markup=keyboard.instruction_menu)

@dp.message(F.text == "Обратиться к ТП")
async def support_handler(message: Message) -> None:
    await message.reply("Связь с ТП.", reply_markup=keyboard.main_menu)

async def main() -> None:
    # Начало опроса обновлений
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
