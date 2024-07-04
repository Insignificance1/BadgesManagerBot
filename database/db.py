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
        except Exception as e:
            print(f"[INFO] Error while connecting to PostgreSQL: {e}")

    # Выполнение SQL-запроса
    def exec_query(self, update, info_message, query_type: bool):
        try:
            # Подключаемся к БД
            connection = ps.connect(
                host=host,
                user=user,
                password=password,
                database=db_name
            )
            connection.autocommit = True
            with connection.cursor() as cursor:
                # Выполняем SQL-запрос
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


    def insert_image(self, id_user, path, id_collection):
        # Отправляем SQL-запрос для добавления изображения в коллекцию
        self.exec_query(f"""
            insert into {schema_name}.images (id_user, path, id_collection)
            values ('{id_user}','{path}', '{id_collection}')
            ""","[INFO] Image was added", True)


    def add_collection(self, id_user, name_collection):
        if 3 <= len(name_collection) <= 100 and not self.contains_collection_name(id_user, name_collection):
            # Отправляем SQL-запрос для добавления коллекции
            query = f"""insert into {schema_name}.collections (id_user, name)
                        values ('{id_user}', '{name_collection}')
                        returning id"""
            try:
                result = self.exec_query(query, "[INFO] Collection was added", True)
                # Получаем id новой коллекции из результата запроса.
                new_collection_id = result[0][0]
                return "Коллекция успешно создана", new_collection_id
            except Exception as e:
                raise Exception("[Ошибка] Произошла ошибка при попытке изменения базы данных. Попробуйте ещё раз.") from e
        else:
            raise Exception("[Ошибка] Неверное название коллекции или коллекция с таким именем уже существует.")


    # вернёт id-коллекции и name-название
    def get_list_collection(self, id_user):
        message = self.exec_query_all(f"""select id, name from {schema_name}.collections where (id_user={id_user})""",
                                 "[INFO] Collection list were received")
        if len(message) == 0:
            return("Нет коллекций")
        else:
            return message


    def get_all_images(self, id_collection):
        return self.exec_query_all(f"""select path from {schema_name}.images where (id_collection={id_collection})""",
                                 "[INFO] Collection list were received")


    def edit_favorites(self, id_collection, is_favorites):
        return self.exec_query(
            f"""update {schema_name}.collections set favorites = {is_favorites} where id = {id_collection}""",
            "[INFO] The collection is marked as favorites", False)


    def get_list_favorites(self, id_user):
        message = self.exec_query_all(f"""select id, name  from {schema_name}.collections where (id_user={id_user} and favorites=true)""",
                                      "[INFO] Favorites list were received")
        if len(message) == 0:
            return ("Нет избранных коллекций")
        else:
            return message


    #по id коллекции заменяет название
    def update_name_collection(self, new_name, id_collection):
        return self.exec_query(
            f"""UPDATE {schema_name}.collections SET name='{new_name}' where id={id_collection}""",
            f"[INFO] Update name collection={new_name} with id={id_collection}",True)


    def contains_collection_name(self, id_user, name):
        result = self.exec_query_all(f"select name from {schema_name}.collections where id_user={id_user} AND name='{name}'",
                                     "[INFO] Checking for existence of collection name")
        return len(result)


    def count_user_collections(self, id_user):
        result = self.exec_query_all(f"select count(*) from {schema_name}.collections where id_user={id_user}",
                                     "[INFO] Counting collections for user")
        return len(result)


    #(get_all_images(4))
    #def del_collection(id_user, id_collection):
    #    if (id_collection==get_list_collection(id_user)):


    #print(get_list_collection(111111111))
    #add_user(111111111)

    # add_collection(1216034152, 'abeb')

    # Пример использования функции
    #n = 44
    # for i in range(0, n, +1):
        # insert_image(id_user=1216034152, path=f'../Photo/noBg/AgACAgIAAxkBAAIL_WaEVVgochVy2L0z1LLPzjAtAprtAAKe3zEbU5EgSPIO6FYarG0EAQADAgADeQADNQQ_{i}.png', collection_id=8)

