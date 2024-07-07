import logging
import asyncio
import os

from bot.settings.variables import bot, dp

from handlers.start_handler import register_start_handlers
from handlers.back_handler import register_back_handlers
from handlers.search_handler import register_search_handlers
from handlers.photo_handler import register_photo_handlers
from handlers.collection_handler import register_collection_handlers
from handlers.image_handler import register_image_handlers
from handlers.favorite_handler import register_favorite_handlers
from handlers.instruction_handler import register_instruction_handlers
from handlers.statistics_handler import register_statistics_handlers

register_start_handlers(dp)
register_back_handlers(dp)
register_search_handlers(dp)
register_photo_handlers(dp)
register_collection_handlers(dp)
register_image_handlers(dp)
register_favorite_handlers(dp)
register_instruction_handlers(dp)
register_statistics_handlers(dp)

# Настройка логирования
logging.basicConfig(level=logging.INFO)


async def main() -> None:
    directories = [
        "../Photo/cut",
        "../Photo/noBg",
        "../Photo/original",
        "../Photo/ZIP/documents",
        "../Photo/statistic",
        "../Photo/PDF"
    ]

    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Создана папка: {directory}")
        else:
            print(f"Папка уже существует: {directory}")
    # Начало опроса обновлений
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
