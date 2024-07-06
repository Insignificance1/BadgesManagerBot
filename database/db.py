import os

import psycopg2 as ps

from database.config import host, user, password, db_name, schema_name


class DataBase:
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
        role = 'user'
        self.exec_query(f"""insert into {schema_name}.users (id, role)
                                          values ('{id}', '{role}')""",
                        "[INFO] User was added", True)

    def log_user_activity(self, user_id, message_id):
        self.exec_query(f"""insert into {schema_name}.user_activity (id, message_id)
                                          values ('{id}', '{message_id}')""",
                        "[INFO] User was added", True)

    def get_role(self, id):
        return self.exec_query(
            f"""select role from {schema_name}.users where id={id}""",
            "[INFO] Collect list null badges", False)

    # Вставка изображения
    def insert_image(self, id_user, path, id_collection):
        # Отправляем SQL-запрос для добавления изображения в коллекцию
        self.exec_query(f"""
            insert into {schema_name}.images (id_user, path, id_collection)
            values ('{id_user}','{path}', '{id_collection}')
            """, "[INFO] Image was added", True)

    #    def add_unique_collection(self, id_user, name):
    #        if 3 <= len(name) <= 100 and not self.contains_collection_name(id_user, name):
    #            query = f"""insert into {schema_name}.collections (id_user, name) values (%s, %s) returning id"""
    #            result = self.exec_query(query, f"[INFO] Collection '{name}' was added", True)
    #            return result[0][0]
    #        else:
    #            raise Exception("[Ошибка] Коллекция с таким именем уже существует.")

    # Добавление коллекции
    def add_collection(self, id_user, name_collection):
        if 3 <= len(name_collection) <= 55 and not self.contains_collection_name(id_user, name_collection):
            # Отправляем SQL-запрос для добавления коллекции
            query = f"""insert into {schema_name}.collections (id_user, name)
                        values ('{id_user}', '{name_collection}')
                        returning id"""
            try:
                result = self.exec_query(query, "[INFO] Collection was added", True)
                # Получаем id новой коллекции из результата запроса.
                new_collection_id = result[0][0]
                return "Коллекция успешно создана.", new_collection_id
            except Exception as e:
                raise Exception("[Ошибка] Произошла ошибка при попытке изменения базы данных.") from e
        else:
            raise Exception("[Ошибка] Неверное название коллекции или коллекция с таким именем уже существует.")

    # Обновление названия значка
    def update_image_name(self, path, name_badge):
        if 3 <= len(name_badge) <= 30:
            try:
                # Отправляем SQL-запрос для изменения названия значка
                self.exec_query(
                    f"""update {schema_name}.images set name='{name_badge}' where path='{path}'""",
                    f"[INFO] Update name collection={name_badge} with path={path}", True)
                return f"Название значка успешно изменено на {name_badge}."
            except Exception as e:
                raise Exception("[Ошибка] Произошла ошибка при попытке изменения базы данных.") from e
        else:
            raise Exception("[Ошибка] Неверное название значка.")

    # Обновление названия коллекции
    def update_collection_name(self, id_user, name_collection, id_collection):
        if 3 <= len(name_collection) <= 100 and not self.contains_collection_name(id_user, name_collection):
            try:
                # Отправляем SQL-запрос для изменения названия коллекции
                self.exec_query(
                    f"""update {schema_name}.collections set name='{name_collection}' where id={id_collection}""",
                    f"[INFO] Update name collection={name_collection} with id={id_collection}", True)
                return f"Название коллекции успешно изменено на {name_collection}."
            except Exception as e:
                raise Exception("[Ошибка] Произошла ошибка при попытке изменения базы данных.") from e
        else:
            raise Exception("[Ошибка] Неверное название коллекции или коллекция с таким именем уже существует.")

    # Обновление количества значков
    def update_image_count(self, path, count):
        try:
            # Отправляем SQL-запрос для изменения количества значков
            self.exec_query(
                f"""update {schema_name}.images set count='{count}' where path='{path}'""",
                f"[INFO] Update image count={count}, where image with path={path}", True)
            return f"Количество значков успешно измененено на {count}."
        except ValueError:
            raise ValueError("[Ошибка] Введённое значение не является числом.")
        except Exception as e:
            raise Exception("[Ошибка] Произошла ошибка при попытке изменения базы данных.") from e

    # Получение списка всех коллекций пользователя
    def get_list_collection(self, id_user):
        message = self.exec_query(f"""select id, name from {schema_name}.collections where (id_user={id_user})""",
                                  "[INFO] Collection list were received", True)
        if len(message) == 0:
            return "Нет коллекций"
        else:
            return message

    def get_null_badges(self, id_collection):
        return self.exec_query(
            f"""select path from {schema_name}.images where id_collection={id_collection} and count=0""",
            "[INFO] Collect list null badges", True)

    def get_list_count(self, id_collection, is_all_count):
        if is_all_count:
            return self.exec_query(f"""select count from {schema_name}.images where id_collection={id_collection}""",
                                   "[INFO] Collect list count all badges", True)
        else:
            return self.exec_query(
                f"""select count from {schema_name}.images where id_collection={id_collection} and count=0""",
                "[INFO] Collect list count null badges", True)

    def get_all_name(self, id_collection, is_all_count):
        if is_all_count:
            return self.exec_query(f"""select name from {schema_name}.images where id_collection={id_collection}""",
                                   "[INFO] Collect list count all badges", True)
        else:
            return self.exec_query(
                f"""select name from {schema_name}.images where id_collection={id_collection} and count=0""",
                "[INFO] Collect list count null badges", True)

    # Получение списка всех избранных (или неизбранных) коллекций пользователя
    def get_list_favorites(self, id_user, is_favorites=True):
        message = self.exec_query(f"select id, name from {schema_name}.collections where id_user={id_user} "
                                  f"and favorites={is_favorites}",
                                  "[INFO] Favorites list were received", True)
        if is_favorites and len(message) == 0:
            return "Нет избранных коллекций"
        else:
            return message

    # Получение списка всех изображений выбранной коллекции
    def get_all_images(self, id_collection):
        return self.exec_query(f"""select path from {schema_name}.images where (id_collection={id_collection})""",
                               "[INFO] Collection list were received", True)

    # Получение названия изображения по указанному пути
    def get_image_name(self, path):
        return self.exec_query(f"""select name from {schema_name}.images where path='{path}'""",
                               "[INFO] Image name was received")

    # Получение количества значков по указанному пути
    def get_image_count(self, path):
        return self.exec_query(f"""select count from {schema_name}.images where path='{path}'""",
                               "[INFO] Image count was received")

    # Изменение флага избранности для выбранной коллекции
    def edit_favorites(self, id_collection, is_favorites):
        return self.exec_query(
            f"""update {schema_name}.collections set favorites = {is_favorites} where id = {id_collection}""",
            "[INFO] The collection is marked as favorites", False)

    # Удаление изображения по указанному пути
    def delete_image(self, path):
        self.exec_query(f"""delete from {schema_name}.images where path ='{path}' """,
                        "[INFO] Images were deleted", True)

    # Удаление коллекции пользователя
    def delete_collection(self, id_user, collection_id):
        # Проверка существования коллекции
        if self.contains_collection(id_user, collection_id):
            # Получение списка изображений, связанных с коллекцией
            images = self.exec_query(f"""select path from {schema_name}.images where id_collection = {collection_id}""",
                                     "[INFO] Images were retrieved", True)
            # Удаление файлов изображений
            for image in images:
                path = image[0]
                self.delete_file_by_path(str(path))
            # Удаление изображений из таблицы images
            self.exec_query(f"""delete from {schema_name}.images where id_collection = {collection_id}""",
                            "[INFO] Images were deleted", True)
            # Удаление коллекции из таблицы collections
            self.exec_query(f"""delete from {schema_name}.collections where id = {collection_id}""",
                            "[INFO] Collection was deleted", True)

            return "Коллекция успешно удалена."
        else:
            raise Exception("[Ошибка] Коллекции не существует.")

    # Удаление файла по указанному пути
    def delete_file_by_path(self, path: str):
        if os.path.exists(path):
            os.remove(path)

    # Проверка наличия коллекции с выбранным id у пользователя
    def contains_collection(self, id_user, collection_id):
        return len(self.exec_query(f"select id from {schema_name}.collections where id={collection_id} "
                                   f"and id_user={id_user}", "[INFO] Return collection"))

    # Проверка наличия коллекции с выбранными именем у пользователя
    def contains_collection_name(self, id_user, name):
        result = self.exec_query(
            f"select name from {schema_name}.collections where id_user={id_user} and name='{name}'",
            "[INFO] Checking for existence of collection name", True)
        return len(result)

    # Подсчёт коллекций пользователя
    def count_user_collections(self, id_user):
        result = self.exec_query(f"select count(*) from {schema_name}.collections where id_user={id_user}",
                                 "[INFO] Counting collections for user", True)
        return len(result)


    #время регистрации юзера
    def get_users_stats(self, start_date, end_date):
        return self.exec_query(f"""SELECT created_at
            FROM {schema_name}.users
            WHERE created_at BETWEEN ('{start_date}') AND ('{end_date}')
            ORDER BY created_at ASC""", "[INFO] Collect stats for users", True)


    #коллекции по имени
    def get_list_collection_for_name(self, id_user, name):
        message = self.exec_query(f"""select id, name from {schema_name}.collections where (id_user={id_user} and name='{name}')""",
                                  "[INFO] Collection list were received", True)
        if len(message) == 0:
            return "Нет коллекций"
        else:
            return message


    def get_image(self, id_image):
        return self.exec_query(f"""select path from {schema_name}.images where (id={id_image})""",
                               "[INFO] Collection path image", True)


    def get_all_images_for_name(self, id_user, name):
        message = self.exec_query(f"""select id, name from {schema_name}.images where (id_user={id_user} and name='{name}')""",
                               "[INFO] Collection list were received", True)
        if len(message) == 0:
            return "Нет значков"
        else:
            return message