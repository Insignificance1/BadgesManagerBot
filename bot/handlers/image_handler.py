from aiogram import Dispatcher, types
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import F

from concurrent.futures import ThreadPoolExecutor

from database.db import DataBase
from bot.states import ImageStates
import bot.keyboard as kb

db = DataBase()
executor = ThreadPoolExecutor()


def register_image_handlers(dp: Dispatcher):
    """
    Редактирование изображений
    """
    import bot.services.image_service as image_service

    @dp.callback_query(lambda c: c.data.startswith('photo_'))
    async def process_edit_callback(callback_query: CallbackQuery, state: FSMContext):
        """
        Обработка действия над изображением
        """
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
            return

        # Редактируем сообщение с изображением
        await image_service.edit_image_message(callback_query, images, edit_idx)
        await state.update_data(edit_idx=edit_idx)

    @dp.message(F.text, ImageStates.waiting_for_image_name)
    async def process_new_name(message: types.Message, state: FSMContext):
        """
        Обработка ввода нового названия значка
        """
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
                await message.reply(str(e), reply_markup=kb.main_menu)
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
                    # Обрабатываем успешную обработку названия
                    await handle_successful_count_update(message, state, data['cq_id'], data['user'], data['chat_ins'],
                                                         data['cq_mes'], new_count, mes_to_del)
                except Exception as e:
                    await message.reply(str(e), reply_markup=kb.main_menu)
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
