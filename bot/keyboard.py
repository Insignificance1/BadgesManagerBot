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
        {
            KeyboardButton(text="Весь список"),
            KeyboardButton(text="Редактировать")
        },
        {
            KeyboardButton(text="Назад"),
            KeyboardButton(text="Удалить")
        }
    ]
)

# Клавиатура редактирования
edit_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Изменить название")],
        [KeyboardButton(text="Добавить")],
        [KeyboardButton(text="Удалить")],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)
