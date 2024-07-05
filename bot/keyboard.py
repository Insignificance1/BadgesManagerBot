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
    ],
    resize_keyboard=True
)

# Клавиавтура коллекций
collections_menu = ReplyKeyboardMarkup(
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
    ],
    resize_keyboard=True
)

# Клавиатура для избранных коллекций
favorite_collections_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Посмотреть избранное"),
            KeyboardButton(text="Изменить название")
        ],
        [
            KeyboardButton(text="Добавить в избранное"),
            KeyboardButton(text="Удалить из избранного")
        ],
        [
            KeyboardButton(text="Выгрузить в PDF"),
            KeyboardButton(text="Назад")
        ]
    ],
    resize_keyboard=True
)

# Клавиатура для коллекций
all_collections_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Изменить название"),
            KeyboardButton(text="Посмотреть коллекцию")
        ],
        [
            KeyboardButton(text="Пополнить коллекцию"),
            KeyboardButton(text="Вывести недостающие значки")
        ],
        [
            KeyboardButton(text="Выгрузить в PDF"),
            KeyboardButton(text="Назад")
        ]
    ],
    resize_keyboard=True
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

# Промежуточная клавиатура между нарезкой фоток и отправкой их
align_menu = ReplyKeyboardMarkup(
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


def create_edit_keyboard(idx, num_objects):
    buttons = [[InlineKeyboardButton(text="Поменять название", callback_data="photo_name")],
               [InlineKeyboardButton(text="Поменять количество", callback_data="photo_count")]]

    if idx == 0:
        buttons.append([
            InlineKeyboardButton(text="✖", callback_data="photo_cross"),
            InlineKeyboardButton(text="➡️", callback_data="photo_next")
        ])
    elif idx == num_objects - 1:
        buttons.append([
            InlineKeyboardButton(text="⬅️", callback_data="photo_prev"),
            InlineKeyboardButton(text="✖", callback_data="photo_cross"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="⬅️", callback_data="photo_prev"),
            InlineKeyboardButton(text="➡️", callback_data="photo_next")
        ])

    buttons.extend([
        [InlineKeyboardButton(text="Удалить", callback_data="photo_del")],
        [InlineKeyboardButton(text="Выход", callback_data="photo_exit")]
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons, row_width=1)
    return keyboard

def create_rotate_keyboard(idx, num_objects):
    buttons = []

    if idx == 0:
        buttons.append([
            InlineKeyboardButton(text="✖", callback_data="rotate_cross"),
            InlineKeyboardButton(text="→", callback_data="rotate_right"),
        ])
    elif idx == num_objects - 1:
        buttons.append([
            InlineKeyboardButton(text="←", callback_data="rotate_left"),
            InlineKeyboardButton(text="✖", callback_data="rotate_cross"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="←", callback_data="rotate_left"),
            InlineKeyboardButton(text="→", callback_data="rotate_right"),
        ])

    buttons.extend([
        [
            InlineKeyboardButton(text="↶ 1°", callback_data="rotate_+1"),
            InlineKeyboardButton(text="↷ 1°", callback_data="rotate_-1"),
        ],
        [
            InlineKeyboardButton(text="↶ 10°", callback_data="rotate_+10"),
            InlineKeyboardButton(text="↷ 10°", callback_data="rotate_-10"),
        ],
        [
            InlineKeyboardButton(text="↶ 45°", callback_data="rotate_+45"),
            InlineKeyboardButton(text="↷ 45°", callback_data="rotate_-45"),
        ],
        [
            InlineKeyboardButton(text="↶ 90°", callback_data="rotate_+90"),
            InlineKeyboardButton(text="↷ 90°", callback_data="rotate_-90"),
        ],
        [
            InlineKeyboardButton(text="Завершить редактирование", callback_data="rotate_continue"),
        ],
        [
            InlineKeyboardButton(text="Выход", callback_data="rotate_exit"),
        ],
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons, row_width=1)
    return keyboard