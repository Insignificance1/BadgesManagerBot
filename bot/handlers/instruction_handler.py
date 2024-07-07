from aiogram import Dispatcher
from aiogram.types import Message
from aiogram import F

import bot.settings.keyboard as kb
from bot.settings.variables import db


def register_instruction_handlers(dp: Dispatcher):
    """
    Инструкция + Тех. поддержка
    """
    @dp.message(F.text == "Инструкция")
    async def instruction_handler(message: Message) -> None:
        """
        Вывод инструкции
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        instruction = (
            "*Рекомендации по улучшению качества нарезки:*\n"
            "1. Сделайте фотографию в высоком разрешении.\n"
            "2. Обеспечьте хорошее освещение.\n"
            "3. Используйте контрастный фон для фотографирования значков.\n"
            "4. Значки должны располагаться на достаточном расстоянии друг от друга.\n\n"
            "*Ограничения:*\n"
            "1. Один пользователь может иметь не более 100 коллекций.\n"
            "2. Одна коллекция может содержать не более 200 фотографий.\n"
            "3. Название коллекции должно содержать от 3 до 55 символов.\n"
            "4. Название значка должно содержать от 3 до 30 символов."
        )
        await message.answer(instruction, reply_markup=kb.instruction_menu, parse_mode='Markdown')

    @dp.message(F.text == "Обратиться к ТП")
    async def support_handler(message: Message) -> None:
        """
        Обращение к ТП
        """
        db.log_user_activity(message.from_user.id, message.message_id)
        answer = (
            "Если у вас есть какие-то вопросы, вы можете обратиться к:\n\n"
            "@insignificance123\n"
            "@Mihter_2208\n"
            "@KatyaPark11\n"
            "@sech14"
        )
        main_menu = kb.create_main_menu(message.from_user.id)
        await message.answer(answer, reply_markup=main_menu)
