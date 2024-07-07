import os
import re
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

import bot.settings.keyboard as kb
from bot.settings.states import ManagerStates


async def generate_user_statistics(list_date, user_id, index):
    """
    Генерация статистики
    """
    df = create_dataframe(list_date)
    user_counts = generate_user_counts(df)

    if not validate_user_counts(user_counts):
        return None

    output_path = create_and_save_plot(user_counts, user_id, index)
    return output_path


def create_dataframe(list_date):
    """
    Создание DataFrame из списка дат
    """
    # Извлекаем даты из кортежей
    formatted_dates = [date[0] for date in list_date]
    # Создаём DataFrame для подсчета уникальных дат
    df = pd.DataFrame({'date': formatted_dates})

    # Приводим столбец 'date' к типу datetime, если он не является таковым
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])
    # Оставляем только дату без времени
    df['date'] = df['date'].dt.date

    return df


def generate_user_counts(df):
    """
    Генерация количества пользователей по датам
    """
    # Группируем по датам и подсчитываем количество пользователей на каждую дату
    user_counts = df['date'].value_counts().sort_index()
    return user_counts


def validate_user_counts(user_counts):
    """
    Проверка наличия данных для создания графика
    """
    if len(user_counts) == 0:
        print("Нет данных для создания графика")
        return False
    return True


def create_and_save_plot(user_counts, user_id, index):
    """
    Создание и сохранение графика на основе данных
    """
    # Создаём график
    plt.figure(figsize=(10, 5))
    plt.plot(user_counts.index, user_counts.values, marker='o', linestyle='-', color='b')
    plt.xlabel('Дата')

    # Устанавливаем названия оси Y и заголовка графика в зависимости от index
    if index == 1:
        plt.ylabel('Количество запросов')
        plt.title('Статистика нагрузки')
    else:
        plt.ylabel('Количество пользователей')
        plt.title('Статистика новых пользователей')

    plt.grid(True)

    # Форматируем ось x для отображения только дат
    plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d'))

    # Создаём папку для хранения графика, если её не существует
    output_dir = os.path.abspath('../../Photo/statistic')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Генерируем пути для сохранения изображения
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_path = os.path.join(output_dir, f'Статистика новых пользователей_{user_id}_{current_time}.png')
    # Сохраняем график в виде изображения
    plt.savefig(output_path)
    plt.close()

    return output_path


async def handle_back_action(message, state, date):
    """
    Обработка команды 'Назад'
    """
    if date == "Назад":
        await state.clear()
        await state.set_state(ManagerStates.manager)
        await message.answer("Вернул вас в меню с функциями: ",
                             reply_markup=kb.manager_function_menu,
                             parse_mode='Markdown')
        return True
    return False


async def handle_invalid_format(message, date_parts):
    """
    Обрабатка случаев неверного формата ввода периода
    """
    if len(date_parts) != 2:
        await message.answer(
            "*Ошибка*: Неверно указан формат, необходимо отправить период в следующем виде: _Год-Месяц-День_ : "
            "_Год-Месяц-День_",
            reply_markup=kb.back_menu,
            parse_mode='Markdown')
        return True
    return False


async def handle_invalid_dates(message, start_date, end_date):
    """
    Обработка случаев неверного формата дат
    """
    date_pattern = r"^\d{4}-\d{2}-\d{2}$"
    if not re.match(date_pattern, start_date) or not re.match(date_pattern, end_date):
        await message.answer(
            "*Ошибка*: Неверно указан формат, необходимо отправить период в следующем виде: _Год-Месяц-День_ : "
            "_Год-Месяц-День_",
            reply_markup=kb.back_menu,
            parse_mode='Markdown')
        return True
    return False


def parse_dates(start_date, end_date):
    """
    Преобразование строки дат в объекты datetime
    """
    start_dates = start_date.split("-")
    end_dates = end_date.split("-")

    d_start_date = datetime(year=int(start_dates[0]), month=int(start_dates[1]), day=int(start_dates[2]),
                            hour=0, minute=0, second=0)
    d_end_date = datetime(year=int(end_dates[0]), month=int(end_dates[1]), day=int(end_dates[2]),
                          hour=23, minute=59, second=59)
    return d_start_date, d_end_date
