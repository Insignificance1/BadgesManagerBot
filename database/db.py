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


def add_user(id):
    role='user'
    exec_query(f"""insert into {schema_name}.users (id, role)
                                      values ('{id}', '{role}')""",
               "[INFO] User was added", True)


def insert_image(id_user, path, collection_id):
    # SQL-запрос для вставки данных
    exec_query(f"""
        INSERT INTO images (id_user, path, id_collection)
        VALUES ('{id_user}','{path}', '{collection_id}')
        ""","[INFO] Image was added", True)

def add_collection(user_id, name_collection):
    if(len(name_collection)>100):
        return("[Ошибка] Количество символов больше 100")
    else:
        exec_query(f"""insert into {schema_name}.collections (id_user, name)
                                                  values ('{user_id}', '{name_collection}')""",
                   "[INFO] Collection was added", True)
        return("Коллекция успешно создана")


#вернёт id-коллекции и name-название
def get_list_collection(id_user):
    message = exec_query_all(f"""select id, name  from public.collections where (id_user={id_user})""",
                             "[INFO] Collection list were received")
    if len(message) ==0:
        return("Нет коллекций")
    else:
        return message


#def del_collection(id_user, id_collection):
#    if (id_collection==get_list_collection(id_user)):


#print(get_list_collection(111111111))
#add_user(111111111)

#add_collection(5740628600,'name')

# Пример использования функции
#insert_image(id_user=111111111, path='D:/dev/Python_dev/Practice/BadgesManagerBot/Photo/noBg/AgACAgIAAxkBAAIJZWaECXmBbCYu90OHLkhPreMGrV9yAAKY3zEbSnYgSIUISBd_YduAAQADAgADeQADNQQ_0.png', collection_id=4)

