import asyncio
import zipfile
import os

from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramBadRequest

from model.convert import Converter
import bot.settings.keyboard as kb
from bot.settings.states import CollectionStates
from bot.settings.variables import bot, db, executor
from bot.services.task_manager import task_manager


async def try_add_collection(message, collection_name):
    """
    Добавление коллекции в БД
    """
    try:
        collection_id = db.add_collection(message.from_user.id, collection_name)[1]
        return collection_id
    except Exception as e:
        await message.reply(str(e) + '\nПопробуйте ещё раз.', reply_markup=kb.back_menu)
        await task_manager.cancel_task_by_name(f'task_{message.from_user.id}')
        await CollectionStates.add_new_collection_zip_name.set()


async def process_and_finalise_zip_file(message, zip_file_id, collection_id, collection_name):
    """
    Обработка архива и завершение процесса создания коллекции
    """
    try:
        await process_zip_file(
            zip_file_id=zip_file_id,
            collection_id=collection_id,
            user_id=message.from_user.id,
            reply_func=lambda: message.reply(f"Коллекция '{collection_name}' успешно создана.",
                                             reply_markup=kb.collections_menu)
        )
        # Завершаем режим ожидания
        await task_manager.cancel_task_by_name(f'task_{message.from_user.id}')
    except Exception as e:
        await message.reply(f"Ошибка при создании коллекции: {e}", kb.collections_menu)
        await task_manager.cancel_task_by_name(f'task_{message.from_user.id}')


async def download_zip_file(zip_file):
    """
    Загрузка архива
    """
    zip_path = f'../Photo/ZIP/{zip_file.file_path}'
    await bot.download_file(zip_file.file_path, zip_path)
    return zip_path


def extract_images_from_zip(zip_path, zip_file_id):
    """
    Распаковка архива и получение списка путей изображений
    """
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        images = []
        for idx, file in enumerate(zip_ref.namelist()):
            filename, file_extension = os.path.splitext(file)
            if file_extension in ['.png', '.jpeg']:
                new_filename = f"{zip_file_id}_{idx}{file_extension}"
                zip_ref.extract(file, '../Photo/noBg/')
                os.rename(f"../Photo/noBg/{file}", f"../Photo/noBg/{new_filename}")
                images.append(new_filename)
    return images


async def insert_images_to_db(images, user_id, collection_id, loop):
    """
    Вставка изображения в БД
    """
    for img_name in images:
        img_path = f"../Photo/noBg/{img_name}"
        await loop.run_in_executor(executor, db.insert_image, user_id, img_path, collection_id)


async def handle_zip_processing(message, collection_id, collection_name, zip_file_id, state):
    """
    Обработка архива и завершение процесса пополнения коллекции
    """
    try:
        await process_zip_file(
            zip_file_id=zip_file_id,
            collection_id=collection_id,
            user_id=message.from_user.id,
            reply_func=lambda: message.reply(f"Коллекция '{collection_name}' успешно пополнена.",
                                             reply_markup=kb.all_collections_menu)
        )
        # Завершаем режим ожидания
        await task_manager.cancel_task_by_name(f'task_{message.from_user.id}')
    except Exception as e:
        await message.reply(f"Ошибка при пополнении коллекции: {e}.", reply_markup=kb.all_collections_menu)
        await task_manager.cancel_task_by_name(f'task_{message.from_user.id}')

    await state.set_state(CollectionStates.collections)


async def process_zip_file(zip_file_id, collection_id, user_id, reply_func):
    """
    Обработка архива
    """
    loop = asyncio.get_running_loop()
    # Загружаем архив
    zip_file = await bot.get_file(zip_file_id)
    zip_path = await download_zip_file(zip_file)
    # Распаковываем архив и обрабатываем изображения
    images = extract_images_from_zip(zip_path, zip_file_id)
    # Удаляем архив после распаковки
    os.remove(zip_path)
    # Добавляем изображения в базу данных
    await insert_images_to_db(images, user_id, collection_id, loop)
    await reply_func()


def determine_type_and_images(data):
    """
    Определение типа коллекции и соответствующей функции для получения изображений
    """
    if data.startswith("pdf_null_"):
        return 1, db.get_null_badges, False
    type_id = 2 if data.startswith("pdf_favorite_") else 1
    return type_id, db.get_all_images, True


async def fetch_collection_data(loop, get_images_func, collection_id, is_all_count):
    """
    Получение данных коллекции
    """
    images_list = await loop.run_in_executor(executor, get_images_func, collection_id)
    count_list = await loop.run_in_executor(executor, db.get_list_count, collection_id, is_all_count)
    name_list = await loop.run_in_executor(executor, db.get_all_name, collection_id, is_all_count)
    return images_list, count_list, name_list


async def convert_to_pdf(loop, name, collection_id, images_list, name_list, count_list):
    """
    Конвертация списка изображений в PDF-файл
    """
    converter = Converter()
    pdf_path = await loop.run_in_executor(executor, converter.convert_to_pdf_ext, name, collection_id,
                                          images_list, name_list, count_list)
    return pdf_path


async def send_pdf_to_user(callback_query, state, pdf_path):
    """
    Отправка PDF-файла пользователю
    """
    try:
        pdf = FSInputFile(pdf_path)
        await bot.delete_message(chat_id=callback_query.message.chat.id,
                                 message_id=callback_query.message.message_id)
        await bot.send_document(chat_id=callback_query.message.chat.id,
                                document=pdf, reply_markup=kb.collections_menu)
        await state.clear()
        os.remove(pdf_path)
    except TelegramBadRequest:
        raise Exception("Что-то пошло не так. Вероятно, кнопка была нажата несколько раз.")
