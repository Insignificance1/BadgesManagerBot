import psycopg2 as ps
import datetime
from database.config import host, user, password, db_name, schema_name

# метод запроса в целом. его можно юзать, когда надо сделть insert, update, delete
# в обшем когда не нужно ничего возвращать
class Db:
    def __init__(self):
        self.connection = 0
    def connect(self):
        try:
            self.connection = ps.connect(
                host=host,
                user=user,
                password=password,
                database=db_name
            )
            self.connection.autocommit = True
        except Exception as ex:
            print(f"[INFO] Error while connecting to PostgreSQL: {ex}")
    def exec_query(self, update, info_message, query_type: bool):
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
    def exec_query_all(self, query, info_message):
        return self.exec_query(query, info_message, True)


    # здесь возвращается первый результат запроса для select
    def exec_query_first(self, query, info_message):
        return self.exec_query( query, info_message, False)


    def add_user(self, id):
        role='user'
        self.exec_query(f"""insert into {schema_name}.users (id, role)
                                          values ('{id}', '{role}')""",
                   "[INFO] User was added", True)


    def insert_image(self, id_user, path, collection_id):
        # SQL-запрос для вставки данных
        self.exec_query(f"""
            INSERT INTO images (id_user, path, id_collection)
            VALUES ('{id_user}','{path}', '{collection_id}')
            ""","[INFO] Image was added", True)

    def add_collection(self, user_id, name_collection):
        if(len(name_collection)>100):
            return("[Ошибка] Количество символов больше 100")
        else:
            self.exec_query(f"""insert into {schema_name}.collections (id_user, name)
                                                      values ('{user_id}', '{name_collection}')""",
                       "[INFO] Collection was added", True)
            return("Коллекция успешно создана")


    #вернёт id-коллекции и name-название
    def get_list_collection(self, id_user):
        message = self.exec_query_all(f"""select id, name  from public.collections where (id_user={id_user})""",
                                 "[INFO] Collection list were received")
        if len(message) ==0:
            return("Нет коллекций")
        else:
            return message


    def get_all_images(self, id_collection):
        return self.exec_query_all(f"""select path from public.images where (id_collection={id_collection})""",
                                 "[INFO] Collection list were received")
    def add_favorities(self, id_collection):
        return self.exec_query(
            f"""insert into favorities from public.collections where (id_collection={id_collection})""",
            "[INFO] Collection list were received", False)

    def get_all_images(self, id_collection):
        return self.exec_query_all(f"""select path from public.images where (id_collection={id_collection})""",
                                 "[INFO] Collection list were received")
    #(get_all_images(4))
    #def del_collection(id_user, id_collection):
    #    if (id_collection==get_list_collection(id_user)):


    #print(get_list_collection(111111111))
    #add_user(111111111)

    #add_collection(759198603,'food')

    # Пример использования функции
    # n = 44
    # for i in range(0, n, +1):
    #     insert_image(id_user=759198603, path=f'../Photo/noBg/AgACAgIAAxkBAAIL_WaEVVgochVy2L0z1LLPzjAtAprtAAKe3zEbU5EgSPIO6FYarG0EAQADAgADeQADNQQ_{i}.png', collection_id=7)

