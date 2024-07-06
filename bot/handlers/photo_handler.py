import asyncio
import os

from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, FSInputFile, Message
from aiogram.fsm.context import FSMContext

from model.convert import Converter

import bot.settings.keyboard as kb
from bot.settings.keyboard import create_rotate_keyboard, remove_keyboard
from bot.settings.states import PhotoStates
from bot.settings.variables import bot, segmenter, db, executor
from bot.services.task_manager import task_manager


def register_photo_handlers(dp: Dispatcher):
    """
    Обработка отправки фото
    """
    import bot.services.photo_service as photo_service

    @dp.message(F.text == "Отправить фото")
    async def send_photo_handler(message: Message, state: FSMContext) -> None:
        """
        Ожидание отправки фото
        """
        await message.answer("Пожалуйста, отправьте фото.", reply_markup=kb.back_menu)
        await state.set_state(PhotoStates.waiting_for_photo)

    @dp.message(F.photo, PhotoStates.waiting_for_photo)
    async def get_photo_handler(message: Message, state: FSMContext) -> None:
        """
        Закачка полученного фото
        """
        photo_id, image_path = await photo_service.download_photo(message)
        await photo_service.update_state_and_reply(message, state, photo_id, image_path)

    @dp.message(F.text == "Посчитать количество", PhotoStates.choose_function_photo)
    async def count_handler(message: Message, state: FSMContext) -> None:
        """
        Подсчёт количества значков на фото
        """
        data = await state.get_data()
        photo_id = data.get('photo_id')
        image_path = data.get('image_path')
        await state.clear()

        # Запускаем параллельную задачу для режима ожидания
        task_manager.create_loading_task(message.chat.id, f'task_{message.from_user.id}')
        # Подсчитываем объекты на изображении
        num_objects = await photo_service.count_objects(image_path)
        # Сообщаем результат пользователю и отменяем задачу ожидания
        await message.answer(f"Количество найденных объектов на фотографии: {num_objects}",
                             reply_markup=kb.function_photo_menu)
        await task_manager.cancel_task_by_name(f'task_{message.from_user.id}')
        await state.set_state(PhotoStates.choose_function_photo)
        await state.update_data(photo_id=photo_id, image_path=image_path)

    @dp.message(F.text == "Нарезать на отдельные значки", PhotoStates.choose_function_photo)
    async def cut_handler(message: Message, state: FSMContext) -> None:
        """
        Нарезка фото на отдельные значки
        """
        data = await state.get_data()
        image_path = data.get('image_path')
        photo_id = data.get('photo_id')
        await state.set_state(PhotoStates.align_function_photo)
        # Запускаем параллельную задачу для режима ожидания
        task_manager.create_loading_task(message.chat.id, f'task_{message.from_user.id}')
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(executor, segmenter.segment_image, image_path, photo_id)
        num_objects = result
        # Завершаем режима ожидания
        await task_manager.cancel_task_by_name(f'task_{message.from_user.id}')
        if num_objects == 0:
            await message.reply("Значков не обнаружено.", reply_markup=kb.main_menu)
        else:
            # Выводим нарезанных фотографий
            for idx in range(num_objects):
                cropped_img_path = f"../Photo/noBg/{photo_id}_{idx}.png"
                photo_cropped = FSInputFile(cropped_img_path)
                await bot.send_photo(chat_id=message.chat.id, photo=photo_cropped, reply_markup=kb.align_menu)
        if num_objects > 200:
            await message.answer("Значков на фото больше 200. Будут доступны только первые 200.")
        await state.update_data(image_path=image_path, photo_id=photo_id, num_objects=num_objects)

    @dp.message(F.text == "Выровнять", PhotoStates.align_function_photo)
    async def align_handler(message: Message, state: FSMContext) -> None:
        """
        Подготовка к выравниванию изображений
        """
        data = await state.get_data()
        photo_id = data.get('photo_id')
        num_objects = data.get('num_objects')
        # Устанавливаем начальный индекс для первого изображения
        idx = 0
        # Указываем путь к выровненному изображению
        aligned_img_path = f"../Photo/noBg/{photo_id}_{idx}.png"
        # Создаём inline клавиатуры
        edit_keyboard = create_rotate_keyboard(idx, num_objects)
        photo_aligned = FSInputFile(aligned_img_path)

        await remove_keyboard(message)
        await bot.send_photo(chat_id=message.chat.id, photo=photo_aligned, reply_markup=edit_keyboard,
                             caption='ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ')
        await state.update_data(edit_idx=idx)

    @dp.callback_query(lambda c: c.data.startswith('rotate_'))
    async def process_rotate_callback(callback_query: CallbackQuery, state: FSMContext) -> None:
        """
        Выравнивание изображений
        """
        data = await state.get_data()
        photo_id = data.get('photo_id')
        edit_idx = data.get('edit_idx')
        num_objects = data.get('num_objects')

        action = callback_query.data.split('_')[-1]

        if action == 'left':
            edit_idx = max(edit_idx - 1, 0)
        elif action == 'right':
            edit_idx += 1
        elif action in ['continue', 'exit']:
            await photo_service.handle_others(action, callback_query)
            return
        else:
            # Парсим угол поворота
            angle = photo_service.parse_rotation_angle(action)
            # Обработка поворота изображения
            await photo_service.process_image_rotation(photo_id, edit_idx, angle)

        # Обновляем изображение
        await photo_service.update_image(photo_id, edit_idx, num_objects, callback_query)
        await state.update_data(edit_idx=edit_idx)
        await callback_query.answer()

    @dp.message(F.text == "Продолжить", PhotoStates.align_function_photo)
    async def continue_handler(message: Message) -> None:
        """
        Продолжение после получения значков после нарезки
        """
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        await message.answer("Коллекция полная?", reply_markup=kb.yes_no_menu)

    @dp.message(F.text == "Да")
    async def yes_handler(message: Message, state: FSMContext) -> None:
        """
        Обработка для полной коллекции после нарезки
        """
        await state.set_state(PhotoStates.all_collection_create)
        await message.answer("Введите название коллекции.", reply_markup=kb.back_menu)

    @dp.message(F.text, PhotoStates.all_collection_create)
    async def create_after_yes_handler(message: Message, state: FSMContext) -> None:
        """
        Создание коллекции после нарезки
        """
        task_manager.create_loading_task(message.chat.id, f'task_{message.from_user.id}')
        main_menu = kb.create_main_menu(message.from_user.id)
        data = await state.get_data()
        try:
            # Добавляем коллекцию в БД
            result = await add_collection_to_db(message.from_user.id, message.text)
            reply, id_collection = result
            num_objects = data.get('num_objects')
            photo_id = data.get('photo_id')
            # Добавляем изображения в коллекцию
            await add_images_to_collection(message.from_user.id, photo_id, num_objects, id_collection)
            await message.reply(reply, reply_markup=main_menu)
            # Завершаем режим ожидания
            await task_manager.cancel_task_by_name(f'task_{message.from_user.id}')
            await state.clear()
        except Exception as e:
            await message.reply(str(e), reply_markup=main_menu)
            await yes_handler(message, state)
            await task_manager.cancel_task_by_name(f'task_{message.from_user.id}')

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

    @dp.message(F.text == "Нет")
    async def no_handler(message: Message, state: FSMContext) -> None:
        """
        Обработка неполной коллекции после нарезки
        """
        task_manager.create_loading_task(message.chat.id, f'task_{message.from_user.id}')

        data = await state.get_data()
        photo_id = data.get('photo_id')
        num_objects = data.get('num_objects')
        zip_path = f'../Photo/ZIP/{photo_id}.zip'

        await create_zip_archive(photo_id, num_objects, zip_path)
        await send_zip_archive(message, zip_path)

        await task_manager.cancel_task_by_name(f'task_{message.from_user.id}')
        await state.clear()
        os.remove(zip_path)

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
