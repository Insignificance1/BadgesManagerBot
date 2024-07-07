import asyncio

from aiogram import types
from aiogram.types import CallbackQuery, Message, FSInputFile, PhotoSize
from aiogram.fsm.context import FSMContext

from model.segment import rotate_image
from model.convert import Converter
import bot.settings.keyboard as kb
from bot.settings.keyboard import create_rotate_keyboard
from bot.settings.states import PhotoStates
from bot.settings.variables import bot, db, segmenter, executor


async def download_photo(message: Message) -> (PhotoSize, str):
    """
    Загрузка фото
    """
    photo_id = message.photo[-1]
    file_info = await bot.get_file(photo_id.file_id)
    image_path = f"../Photo/original/{photo_id.file_id}.jpg"
    await bot.download_file(file_path=file_info.file_path, destination=image_path)
    return photo_id, image_path


async def update_state_and_reply(message: Message, state: FSMContext, photo_id: PhotoSize, image_path: str) -> None:
    """
    Обновление состояния и ответ пользователю о получении фото
    """
    await message.answer("Фото получено.", reply_markup=kb.function_photo_menu)
    await state.clear()
    await state.update_data(image_path=image_path, photo_id=photo_id.file_id)
    await state.set_state(PhotoStates.choose_function_photo)


async def count_objects(image_path: str) -> int:
    """
    Подсчёт объектов на фото
    """
    loop = asyncio.get_running_loop()
    num_objects = await loop.run_in_executor(None, segmenter.get_count, image_path)
    return num_objects


async def handle_others(action: str, callback_query: CallbackQuery) -> None:
    """
    Обработка других действий (продолжение и выход)
    """
    if action == 'continue':
        await bot.send_message(chat_id=callback_query.message.chat.id, text="Коллекция полная?",
                               reply_markup=kb.yes_no_menu)
    else:
        main_menu = kb.create_main_menu(callback_query.from_user.id)
        await bot.send_message(chat_id=callback_query.message.chat.id, text="Вы вернулись в главное меню.",
                               reply_markup=main_menu)
    # Удаляем клавиатуру
    await bot.delete_message(chat_id=callback_query.message.chat.id,
                             message_id=callback_query.message.message_id)
    await callback_query.answer()


def parse_rotation_angle(action: str) -> int:
    """
    Парсинг угла поворота
    """
    try:
        return int(action)
    except ValueError:
        raise ValueError("Обнаружено несуществующее действие")


async def process_image_rotation(photo_id: PhotoSize, edit_idx: int, angle: int) -> None:
    """
    Обработка поворота изображения
    """
    image_path = f"../Photo/noBg/{photo_id}_{edit_idx}.png"
    if angle != 0:
        rotate_image(image_path, angle)


async def update_image(photo_id: PhotoSize, edit_idx: int, num_objects: int, callback_query: CallbackQuery) -> None:
    """
    Обновление изображения inline клавиатуры
    """
    image_path = f"../Photo/noBg/{photo_id}_{edit_idx}.png"
    edit_keyboard = create_rotate_keyboard(edit_idx, num_objects)
    photo_aligned = FSInputFile(image_path)

    await bot.edit_message_media(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        media=types.InputMediaPhoto(media=photo_aligned,
                                    caption='ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ'),
        reply_markup=edit_keyboard
    )


async def add_collection_to_db(user_id: int, collection_name: str) -> tuple:
    """
    Добавление коллекции в БД
    """
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(executor, db.add_collection, user_id, collection_name)
    return result


async def add_images_to_collection(user_id: int, photo_id: int, num_objects: int, id_collection: int) -> None:
    """
    Добавление изображений в коллекцию
    """
    loop = asyncio.get_running_loop()
    for idx in range(min(num_objects, 200)):
        img_path = f"../Photo/noBg/{photo_id}_{idx}.png"
        await loop.run_in_executor(executor, db.insert_image, user_id, img_path, id_collection)


async def create_zip_archive(photo_id: int, num_objects: int, zip_path: str) -> None:
    """
    Создание архива с изображениями
    """
    converter = Converter()
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(executor, converter.convert_to_zip, photo_id, num_objects, zip_path)


async def send_zip_archive(message: Message, zip_path: str) -> None:
    """
    Отправка ZIP архива пользователю
    """
    zip_file = FSInputFile(zip_path)
    main_menu = kb.create_main_menu(message.from_user.id)
    await message.reply("В таком случае держите архив с размеченными значками.", reply_markup=main_menu)
    await bot.send_document(chat_id=message.chat.id, document=zip_file)
