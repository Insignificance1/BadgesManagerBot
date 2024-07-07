from aiogram import Dispatcher, types
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram import F

from bot.settings.states import ImageStates
import bot.settings.keyboard as kb
from bot.settings.keyboard import create_edit_keyboard
from bot.services.other_service import get_collection_id_and_name
from bot.settings.variables import bot, db


def register_image_handlers(dp: Dispatcher):
    """
    Редактирование изображений
    """
    import bot.services.image_service as image_service

    @dp.callback_query(lambda c: c.data.startswith('show_collection_') or c.data.startswith('show_favorite_'))
    async def process_edit_callback(callback_query: CallbackQuery, state: FSMContext):
        """
        Создание inline клавиатуры для редактирования изображений
        """
        db.log_user_activity(callback_query.from_user.id, callback_query.inline_message_id)
        # Получаем id и название коллекции
        type_id = 2 if callback_query.data.startswith("show_favorite_") else 1
        collection_id = (await get_collection_id_and_name(callback_query, type_id=type_id))[0]
        # Получаем изображения в выбранной коллекции
        images = db.get_all_images(collection_id)
        # Преобразуем результат запроса в список путей
        formatted_images = [row[0] for row in images]
        # Отправляем inline клавиатуру с первым изображением
        name = db.get_image_name(formatted_images[0])[0]
        count = db.get_image_count(formatted_images[0])[0]
        await bot.send_photo(chat_id=callback_query.message.chat.id, photo=FSInputFile(str(formatted_images[0])),
                             reply_markup=create_edit_keyboard(0, len(formatted_images)),
                             caption=f'ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ\nНазвание: {name}\nКоличество: {count}')
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await state.update_data(images=formatted_images, edit_idx=0, mes_to_del=[])

    @dp.callback_query(lambda c: c.data.startswith('search_collection_'))
    async def process_edit_callback(callback_query: CallbackQuery, state: FSMContext):
        """
        Создание inline клавиатуры для редактирования изображений
        """
        db.log_user_activity(callback_query.from_user.id, callback_query.inline_message_id)
        # Получаем id и название коллекции
        collection_id = int(callback_query.data.split("_")[2])
        # Получаем изображения в выбранной коллекции
        images = db.get_all_images(collection_id)
        # Преобразуем результат запроса в список путей
        formatted_images = [row[0] for row in images]
        # Отправляем inline клавиатуру с первым изображением
        name = db.get_image_name(formatted_images[0])[0]
        count = db.get_image_count(formatted_images[0])[0]
        await bot.send_photo(chat_id=callback_query.message.chat.id, photo=FSInputFile(str(formatted_images[0])),
                             reply_markup=create_edit_keyboard(0, len(formatted_images)),
                             caption=f'ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ\nНазвание: {name}\nКоличество: {count}')
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await state.update_data(images=formatted_images, edit_idx=0, mes_to_del=[])


    @dp.callback_query(lambda c: c.data.startswith('show_badge_'))
    async def process_edit_image_callback(callback_query: CallbackQuery, state: FSMContext):
        """
        Создание inline клавиатуры для редактирования изображения
        """
        db.log_user_activity(callback_query.from_user.id, callback_query.inline_message_id)
        id = int(callback_query.data.split("_")[2])
        # Получаем изображение
        image = db.get_image(id)
        path = str(image[0][0])
        # Отправляем inline клавиатуру с первым изображением
        name = db.get_image_name(path)[0]
        count = db.get_image_count(path)[0]
        await bot.send_photo(chat_id=callback_query.message.chat.id, photo=FSInputFile(path),
                             reply_markup=create_edit_keyboard(0, len(image)),
                             caption=f'ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ\nНазвание: {name}\nКоличество: {count}')
        await bot.delete_message(chat_id=callback_query.message.chat.id,
                                 message_id=callback_query.message.message_id)
        await state.update_data(images=image, edit_idx=0, mes_to_del=[])


    @dp.callback_query(lambda c: c.data.startswith('image_'))
    async def process_edit_callback(callback_query: CallbackQuery, state: FSMContext):
        """
        Обработка действия над изображением
        """
        db.log_user_activity(callback_query.from_user.id, callback_query.inline_message_id)
        data = await state.get_data()
        images = data.get('images')
        edit_idx = data.get('edit_idx')
        action = callback_query.data.split('_')[-1]

        # Выполняем указанное действие над изображением
        if action == 'prev':
            edit_idx = await image_service.handle_prev_action(state, edit_idx)
        elif action == 'next':
            edit_idx = await image_service.handle_next_action(state, edit_idx)
        elif action == 'del':
            edit_idx = await image_service.handle_delete_action(images, edit_idx)
        elif action == 'name':
            await image_service.handle_name_action(callback_query, state, edit_idx, data)
            return
        elif action == 'count':
            await image_service.handle_count_action(callback_query, state, edit_idx, data)
            return
        elif action == 'exit':
            await image_service.handle_exit_action(callback_query)
            await state.clear()
            return

        # Редактируем сообщение с изображением
        await image_service.edit_image_message(callback_query, images, edit_idx)
        await state.update_data(edit_idx=edit_idx)

    @dp.message(F.text, ImageStates.waiting_for_image_name)
    async def process_new_name(message: types.Message, state: FSMContext):
        """
        Обработка ввода нового названия значка
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        new_name = message.text
        data = await state.get_data()
        mes_to_del = data.get('mes_to_del', [])
        mes_to_del.append(message.message_id)

        if 3 <= len(new_name) <= 30:
            try:
                # Обновляем название изображения в БД
                image_path = data['images'][data['edit_idx']]
                db.update_image_name(image_path, new_name)
                # Обрабатываем успешную обработку названия
                await handle_successful_name_update(message, state, data['cq_id'], data['user'], data['chat_ins'],
                                                    data['cq_mes'], new_name, mes_to_del)
            except Exception as e:
                await message.reply(str(e), reply_markup=kb.collections_menu)
                await handle_successful_name_update(message, state, data['cq_id'], data['user'], data['chat_ins'],
                                                    data['cq_mes'], new_name, mes_to_del)
        else:
            mes = await message.reply(
                "[Ошибка] Неверное название значка. Название должно содержать от 3 до 30 символов.")
            mes_to_del.append(mes.message_id)

    async def handle_successful_name_update(message, state, cq_id, user, chat_ins, cq_mes, new_name, mes_to_del):
        """
        Обработка успешного обновления названия изображения
        """
        await state.update_data(new_name=new_name, mes_to_del=mes_to_del)
        # Возвращаемся в режим редактирования изображений
        await process_edit_callback(CallbackQuery(id=cq_id, from_user=user, chat_instance=chat_ins,
                                                  data="photo_newname", message=cq_mes), state)
        await image_service.delete_old_messages(message.chat.id, mes_to_del)
        await state.update_data(mes_to_del=[])

    @dp.message(F.text, ImageStates.waiting_for_image_count)
    async def process_new_count(message: types.Message, state: FSMContext):
        """
        Обработка ввода нового количества значков
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        data = await state.get_data()
        mes_to_del = data.get('mes_to_del', [])
        mes_to_del.append(message.message_id)
        try:
            new_count = int(message.text)
            if 0 <= new_count <= 32767:
                try:
                    # Обновляем количество значков в БД
                    image_path = data['images'][data['edit_idx']]
                    db.update_image_count(image_path, new_count)
                    # Обрабатываем успешную обработку количества
                    await handle_successful_count_update(message, state, data['cq_id'], data['user'], data['chat_ins'],
                                                         data['cq_mes'], new_count, mes_to_del)
                except Exception as e:
                    await message.reply(str(e), reply_markup=kb.collections_menu)
                    await handle_successful_count_update(message, state, data['cq_id'], data['user'], data['chat_ins'],
                                                         data['cq_mes'], new_count, mes_to_del)
            else:
                mes = await message.reply("[Ошибка] Количество значков должно быть положительным числом.")
                mes_to_del.append(mes.message_id)
        except ValueError:
            mes = await message.reply("[Ошибка] Пожалуйста, введите корректное число для количества значков.")
            mes_to_del.append(mes.message_id)

    async def handle_successful_count_update(message, state, cq_id, user, chat_ins, cq_mes, new_count, mes_to_del):
        """
        Обработка успешного обновления количества значков
        """
        await state.update_data(new_count=new_count)
        # Возвращаемся в режим редактирования изображений
        await process_edit_callback(CallbackQuery(id=cq_id, from_user=user, chat_instance=chat_ins,
                                                  data="photo_newcount", message=cq_mes), state)
        await image_service.delete_old_messages(message.chat.id, mes_to_del)
        await state.update_data(mes_to_del=[])
