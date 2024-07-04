from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Основная клавиатура
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Отправить фото"),
            KeyboardButton(text="Коллекции")
        ],
        [KeyboardButton(text="Инструкция")]
    ],
    resize_keyboard=True
)

# Клавитура с функциями обработки фото
function_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Посчитать количество"),
            KeyboardButton(text="Нарезать на отдельные значки")
        ],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)

# Клавиатура ответа на вопрос о полноте коллекции после нарезки
yes_no_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Да"),
            KeyboardButton(text="Нет")
        ],
        [KeyboardButton(text="Назад")]
    ]
)

# Клавиавтура коллекций
collection_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Избранное"),
            KeyboardButton(text="Весь список")
        ],
        [
            KeyboardButton(text="Добавить коллекцию"),
            KeyboardButton(text="Удалить коллекцию")
        ],
        [KeyboardButton(text="Назад")]
    ]
)

favorite_collection_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Добавить в избранное"),
            KeyboardButton(text="Удалить из избранного")
        ],
        [
            KeyboardButton(text="Изменить название"),
            KeyboardButton(text="Назад")
        ]
    ],
    resize_keyboard=True
)

# Клавиатура для коллекций
edit_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Изменить название"),
            KeyboardButton(text="Посмотреть коллекцию")
        ],
        [
            KeyboardButton(text="Добавить значок в коллекцию"),
            KeyboardButton(text="Вывести недостающие значки")
        ],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)

# Клавиатура редактирований коллекций
keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Поменять название", callback_data="change_name")],
        [InlineKeyboardButton(text="Поменять количество", callback_data="change_count")],
        [
            InlineKeyboardButton(text="⬅️", callback_data="prev"),
            InlineKeyboardButton(text="➡️", callback_data="next")
        ],
        [InlineKeyboardButton(text="❌", callback_data="del")]
    ]
)

# Клавиатура инструкции
instruction_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Обратиться к ТП"),
            KeyboardButton(text="Назад")
        ]
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