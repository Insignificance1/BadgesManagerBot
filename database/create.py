import psycopg2
#код для переноса бд на другой пк, только структура
# Параметры подключения к базе данных
db_params = {
    'dbname': 'mydatabase',
    'user': 'yourusername',
    'password': 'yourpassword',
    'host': 'localhost',
    'port': 5432
}

# Подключаемся к базе данных
conn = psycopg2.connect(**db_params)
cursor = conn.cursor()

# Создаем таблицы
create_tables_query = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    role VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS collections (
    id SERIAL PRIMARY KEY,
    id_user INTEGER REFERENCES users(id),
    name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS images (
    id SERIAL PRIMARY KEY,
    id_user INTEGER REFERENCES users(id),
    path VARCHAR(255),
    photo BYTEA,
    id_collection INTEGER REFERENCES collections(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Выполняем запрос на создание таблиц
cursor.execute(create_tables_query)
conn.commit()

# Закрываем соединение с базой данных
cursor.close()
conn.close()

print("База данных и таблицы успешно созданы.")
