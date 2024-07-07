import asyncio
import zipfile
import os
from typing import List, Callable
from aiogram.methods.send_message import SendMessage
from aiogram.types import Message, File

import bot.settings.keyboard as kb
from bot.settings.states import CollectionStates
from bot.settings.variables import bot, db, executor
from bot.services.task_manager import task_manager


async def try_add_collection(message: Message, collection_name: str) -> int:
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


async def process_and_finalise_zip_file(message: Message, zip_file_id: str, collection_id: int,
                                        collection_name: str) -> None:
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


async def process_zip_file(zip_file_id: str, collection_id: int, user_id: int,
                           reply_func: Callable[[], SendMessage]) -> None:
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


async def download_zip_file(zip_file: File) -> str:
    """
    Загрузка архива
    """
    zip_path = f'../Photo/ZIP/{zip_file.file_path}'
    await bot.download_file(zip_file.file_path, zip_path)
    return zip_path


def extract_images_from_zip(zip_path: str, zip_file_id: str) -> List[str]:
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


async def insert_images_to_db(images: List[str], user_id: int, collection_id: int,
                              loop: asyncio.AbstractEventLoop) -> None:
    """
    Вставка изображения в БД
    """
    for img_name in images:
        img_path = f"../Photo/noBg/{img_name}"
        await loop.run_in_executor(executor, db.insert_image, user_id, img_path, collection_id)
