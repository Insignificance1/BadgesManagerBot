import asyncio
from concurrent.futures import ThreadPoolExecutor

from database.db import DataBase

db = DataBase()
executor = ThreadPoolExecutor()


async def get_collection_id_and_name(callback_query, loop=None, type_id=1):
    """
    Получение id и названия коллекции
    """
    if loop is None:
        loop = asyncio.get_running_loop()
    user_id = callback_query.from_user.id
    # Ищем id коллекции и её название в БД
    if type_id == 1:
        db_message = await loop.run_in_executor(executor, db.get_list_collection, user_id)
    elif type_id == 2:
        db_message = await loop.run_in_executor(executor, db.get_list_favorites, user_id)
    elif type_id == 3:
        db_message = await loop.run_in_executor(executor, db.get_list_collection, user_id)
    else:
        db_message = await loop.run_in_executor(executor, db.get_list_favorites, user_id, False)
    collection_id, name = db_message[int(callback_query.data.split("_")[2]) - 1]
    return collection_id, name