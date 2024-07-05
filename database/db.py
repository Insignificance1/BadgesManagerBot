import psycopg2 as ps
import datetime
from database.config import host, user, password, db_name, schema_name

class DataBase:
    def __init__(self):
        self.connection = 0

    # Выполнение SQL-запроса
    def exec_query(self, update, info_message, is_all_strs=False):
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
                if is_all_strs:
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

    # Добавление нового пользователя
    def add_user(self, id):
        role='user'
        self.exec_query(f"""insert into {schema_name}.users (id, role)
                                          values ('{id}', '{role}')""",
                   "[INFO] User was added", True)

    # Вставка изображения
    def insert_image(self, id_user, path, id_collection):
        # Отправляем SQL-запрос для добавления изображения в коллекцию
        self.exec_query(f"""
            insert into {schema_name}.images (id_user, path, id_collection)
            values ('{id_user}','{path}', '{id_collection}')
            ""","[INFO] Image was added", True)

#    def add_unique_collection(self, id_user, name):
#        if 3 <= len(name) <= 100 and not self.contains_collection_name(id_user, name):
#            query = f"""insert into {schema_name}.collections (id_user, name) values (%s, %s) returning id"""
#            result = self.exec_query(query, f"[INFO] Collection '{name}' was added", True)
#            return result[0][0]
#        else:
#            raise Exception("[Ошибка] Коллекция с таким именем уже существует.")

    # Добавление коллекции
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

    # Обновление названия коллекции
    def update_collection_name(self, id_user, name_collection, id_collection):
        if 3 <= len(name_collection) <= 100 and not self.contains_collection_name(id_user, name_collection):
            try:
                # Отправляем SQL-запрос для изменения названия коллекции
                self.exec_query(
                    f"""update {schema_name}.collections set name='{name_collection}' where id={id_collection}""",
                    f"[INFO] Update name collection={name_collection} with id={id_collection}", True)
                return f"Название коллекции успешно измененено на {name_collection}."
            except Exception as e:
                raise Exception("[Ошибка] Произошла ошибка при попытке изменения базы данных. Попробуйте ещё раз.") from e
        else:
            raise Exception("[Ошибка] Неверное название коллекции или коллекция с таким именем уже существует.")

    # Получение списка всех коллекций пользователя
    def get_list_collection(self, id_user):
        message = self.exec_query(f"""select id, name from {schema_name}.collections where (id_user={id_user})""",
                                 "[INFO] Collection list were received", True)
        if len(message) == 0:
            return("Нет коллекций")
        else:
            return message

    # Получения списка всех избранных (или неизбранных) коллекций пользователя
    def get_list_favorites(self, id_user, is_favorites=True):
        message = self.exec_query(f"select id, name from {schema_name}.collections where id_user={id_user} "
                                  f"and favorites={is_favorites}",
                                  "[INFO] Favorites list were received", True)
        if is_favorites and len(message) == 0:
            return ("Нет избранных коллекций")
        else:
            return message

    # Получение списка всех изображений выбранной коллекции
    def get_all_images(self, id_collection):
        return self.exec_query(f"""select path from {schema_name}.images where (id_collection={id_collection})""",
                                 "[INFO] Collection list were received", True)

    # Изменение флага избранности для выбранной коллекции
    def edit_favorites(self, id_collection, is_favorites):
        return self.exec_query(
            f"""update {schema_name}.collections set favorites = {is_favorites} where id = {id_collection}""",
            "[INFO] The collection is marked as favorites", False)

    # Проверка наличия коллекции с выбранными именем у пользователя
    def contains_collection_name(self, id_user, name):
        result = self.exec_query(f"select name from {schema_name}.collections where id_user={id_user} and name='{name}'",
                                     "[INFO] Checking for existence of collection name", True)
        return len(result)

    # Подсчёт коллекций пользователя
    def count_user_collections(self, id_user):
        result = self.exec_query(f"select count(*) from {schema_name}.collections where id_user={id_user}",
                                     "[INFO] Counting collections for user", True)
        return len(result)