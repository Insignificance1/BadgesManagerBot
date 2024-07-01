import psycopg2 as ps
import datetime
from database.config import host, user, password, db_name, schema_name

# метод запроса в целом. его можно юзать, когда надо сделть insert, update, delete
# в обшем когда не нужно ничего возвращать
def exec_query(update, info_message, query_type: bool):
    try:
        connection = ps.connect(
            host=host,
            user=user,
            password=password,
            database=db_name
        )
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(update)
            print(info_message)
            if query_type:
                result = cursor.fetchall()
            else:
                result = cursor.fetchone()
        return result
    except Exception as _ex:
        print("[INFO] Error while working with PostgreSQL", _ex)
    finally:
        if connection:
            connection.close()
            print("[INFO] PostgreSQL connection closed")

# здесь возвращаются все результаты запроса для select
def exec_query_all(query, info_message):
    return exec_query(query, info_message, True)


# здесь возвращается первый результат запроса для select
def exec_query_first(query, info_message):
    return exec_query(query, info_message, False)