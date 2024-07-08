import psycopg2
#код для переноса бд на другой пк, только структура
#Если вы вносите здесь изменения  и создаёте базу данных, то необходимо внести соответствующие изменения в файл: BadgesManagerBot/database/config.py
#после это все подключения будут к созданной бд
# Параметры подключения к базе данных
db_params = {
    'dbname': 'badges_manager',#название вашей базы данных(она будет создана автоматически или будет использованна уже существующая)
    'user': 'yourusername',#ваше имя пользователя(необхдимо редактировать)
    'password': 'yourpassword',#пароль пользователя(необхдимо редактировать)
    'host': 'localhost',
    'port': 5432
}

# Подключаемся к базе данных
conn = psycopg2.connect(**db_params)
cursor = conn.cursor()

# Создаем таблицы
create_tables_query = """
CREATE TABLE IF NOT EXISTS users (
    id bigserial NOT NULL,
    "role" varchar(50) NOT NULL,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT users_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS collections (
    id serial4 NOT NULL,
    id_user int8 NOT NULL,
    "name" varchar(55) NOT NULL,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    favorites bool NOT NULL DEFAULT false,
    CONSTRAINT collections_pkey PRIMARY KEY (id),
    CONSTRAINT collections_id_user_fkey FOREIGN KEY (id_user) REFERENCES public.users(id)
);

CREATE TABLE IF NOT EXISTS images (
    id serial4 NOT NULL,
    id_user int8 NOT NULL,
    "path" varchar(255) NOT NULL,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    id_collection int4 NOT NULL,
    "name" varchar(30) NOT NULL DEFAULT 'Безымянный',
    count int2 NOT NULL DEFAULT 0,
    CONSTRAINT images_pkey PRIMARY KEY (id),
    CONSTRAINT images_id_collection_fkey FOREIGN KEY (id_collection) REFERENCES public.collections(id) ON DELETE CASCADE,
    CONSTRAINT images_id_user_fkey FOREIGN KEY (id_user) REFERENCES public.users(id)
);

CREATE TABLE IF NOT EXISTS user_activity (
    id serial4 NOT NULL,
    user_id int8 NOT NULL,
    message_id int8 NOT NULL,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT user_activity_pkey PRIMARY KEY (id),
    CONSTRAINT user_activity_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
"""

# Выполняем запрос на создание таблиц
cursor.execute(create_tables_query)
conn.commit()

# Закрываем соединение с базой данных
cursor.close()
conn.close()

print("База данных и таблицы успешно созданы.")
