import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime


async def generate_user_statistics(list_date, user_id):
    # Извлечение дат из кортежей
    formatted_dates = [date[0] for date in list_date]

    # Создание DataFrame для подсчета уникальных дат
    df = pd.DataFrame({'date': formatted_dates})

    # Приводим столбец 'date' к типу datetime, если он не является таковым
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])

    # Оставляем только дату без времени
    df['date'] = df['date'].dt.date

    # Группировка по датам и подсчет количества пользователей на каждую дату
    user_counts = df['date'].value_counts().sort_index()

    # Проверяем, есть ли данные для создания графика
    if len(user_counts) == 0:
        print("Нет данных для создания графика")
        return None

    # Создание графика
    plt.figure(figsize=(10, 5))
    plt.plot(user_counts.index, user_counts.values, marker='o', linestyle='-', color='b')
    plt.xlabel('Дата регистрации')
    plt.ylabel('Количество пользователей')
    plt.title('Статистика новых пользователей')
    plt.grid(True)

    # Форматирование оси x для отображения только дат
    plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d'))

    # Создание папки для хранения графика, если её не существует
    output_dir = os.path.abspath('../../Photo/statistic')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Генерация пути для сохранения изображения
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_path = os.path.join(output_dir, f'Статистика новых пользователей_{user_id}_{current_time}.png')

    # Сохранение графика в виде изображения
    plt.savefig(output_path)
    plt.close()

    return output_path
