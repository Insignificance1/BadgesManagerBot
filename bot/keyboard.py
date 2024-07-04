from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


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

# Промежуточная клавиатура между нарезкой фоток и отправкой их
function2_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Выровнять")],
        [KeyboardButton(text="Продолжить")],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)

# Клавиатура после перехода в выравнивание
function3_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Редактировать")],
        [KeyboardButton(text="Продолжить")],
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


def create_edit_keyboard(idx, num_objects):
    buttons = []

    if idx == 0:
        buttons.append([
            InlineKeyboardButton(text="✖", callback_data="edit_cross"),
            InlineKeyboardButton(text="→", callback_data="edit_right"),
        ])
    elif idx == num_objects - 1:
        buttons.append([
            InlineKeyboardButton(text="←", callback_data="edit_left"),
            InlineKeyboardButton(text="✖", callback_data="edit_cross"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="←", callback_data="edit_left"),
            InlineKeyboardButton(text="→", callback_data="edit_right"),
        ])

    buttons.extend([
        [
            InlineKeyboardButton(text="↶ 1°", callback_data="edit_+1"),
            InlineKeyboardButton(text="↷ 1°", callback_data="edit_-1"),
        ],
        [
            InlineKeyboardButton(text="↶ 10°", callback_data="edit_+10"),
            InlineKeyboardButton(text="↷ 10°", callback_data="edit_-10"),
        ],
        [
            InlineKeyboardButton(text="↶ 45°", callback_data="edit_+45"),
            InlineKeyboardButton(text="↷ 45°", callback_data="edit_-45"),
        ],
        [
            InlineKeyboardButton(text="↶ 90°", callback_data="edit_+90"),
            InlineKeyboardButton(text="↷ 90°", callback_data="edit_-90"),
        ],
        [
            InlineKeyboardButton(text="Завершить редактирование", callback_data="edit_continue"),
        ],
        [
            InlineKeyboardButton(text="Выход", callback_data="edit_exit"),
        ],
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
