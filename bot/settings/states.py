from aiogram.fsm.state import State, StatesGroup


# Состояния FSM
class States(StatesGroup):
    waiting_for_zip_create = State()  # Состояние ожидания ZIP-файла при создании коллекции
    waiting_for_zip_add = State()  # Состояние ожидания ZIP-файла при пополнении коллекции
    waiting_for_photo = State()  # Ожидание фото для разметки
    choose_function_photo = State()  # Ожидание выбора функции обработки фото
    align_function_photo = State()  # Ожидание выравнивание значков
    change_collection_name = State()  # Ожидание ввода названия коллекции
    add_new_collection_zip_name = State()  # Ожидание создание новой колекции из ZIP файла с именем
    add_badge = State()  # Ожидание фото значка в модуле редактирования
    collections = State()  # Состояние для выгрузки PDF файла из всего списка
    favorites = State()  # Состояние для выгрузки PDF файла из избранного
    state_null_badges = State()  # Состояние для выгрузки PDF файла с 0 значками
    state_list = State()  # Состояние считывания сообщения с номером коллекции
    state_favorite_list = State()  # Состояние считывания сообщения с номером избранной коллекции
    state_add_favorite_list = State()  # Состояние считывания сообщения с номером коллекции для добавления в избранное
    state_del_favorite_list = State()  # Состояние считывания сообщения с номером коллекции для удаления из избранного
    change_favorite_collection_name = State()  # Состояние ожидания ввода названия избранной коллекции
    waiting_for_new_name = State()  # Ожидает задания имени
    state_back = State()  # Ждёт кнопки назад
    state_del_collection = State()  # Состояние ожидания удаления коллекции
    all_collection_create = State()
    align_state = State()
    waiting_for_name_collection = State()
    waiting_for_name_favorite = State()


# Состояния при редактировании изображений
class ImageStates(StatesGroup):
    waiting_for_image_name = State()    # Ожидание ввода названия изображения
    waiting_for_image_count = State()   # Ожидание ввода количества
