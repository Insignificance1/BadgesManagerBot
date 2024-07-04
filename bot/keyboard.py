from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Основная клавиатура
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Отправить фото")],
        [KeyboardButton(text="Коллекции")],
        [KeyboardButton(text="Инструкция")]
    ],
    resize_keyboard=True
)

# Клавиатура инструкции
instruction_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Обратиться к ТП")],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)

# Клавитура с функциями
function_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Посчитать количество")],
        [KeyboardButton(text="Нарезать на отдельные значки")],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)

yes_no_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Да")],
        [KeyboardButton(text="Нет")],
        [KeyboardButton(text="Назад")]
    ]
)

# Клавиавтура коллекций
collection_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Избранное"),
            KeyboardButton(text="Добавить")
        ],
        [
            KeyboardButton(text="Весь список"),
            KeyboardButton(text="Редактировать")
        ],
        [
            KeyboardButton(text="Назад"),
            KeyboardButton(text="Удалить")
        ]
    ]
)

favorite_collection_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Изменить название")],
        [KeyboardButton(text="Добавить в избранное")],
        [KeyboardButton(text="Удалить из избранного")],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)

# Клавиатура редактирования коллекции
edit_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Изменить название")],
        [KeyboardButton(text="Добавить значок")],
        [KeyboardButton(text="Удалить значок")],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)

# Промежуточная клавиатура
back_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)