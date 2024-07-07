from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    """
    Состояния для поиска
    """
    waiting_for_search = State()  # Ждёт ввода пользователя для поиска


class ManagerStates(StatesGroup):
    """
    Состояния для работы менеджера
    """
    manager = State()                   # Отделение функций менеджера от пользователя
    input_period_attendance = State()   # Ожидание ввода периода от менеджера
    input_period_workload = State()     # Ожидание ввода периода от менеджера для статистики нагрузки
    input_period_new_users = State()    # Ожидание ввода периода от менеджера для статистики пользователей
    manager_new_user = State()          # Ожидание просмотра новых пользователей
    manager_workload = State()          # Ожидание просмотра загруженности бота


class ImageStates(StatesGroup):
    """
    Состояния при редактировании изображений
    """
    waiting_for_image_name = State()    # Ожидание ввода названия изображения
    waiting_for_image_count = State()   # Ожидание ввода количества


class PhotoStates(StatesGroup):
    """
    Состояния при отправке и обработке фото
    """
    waiting_for_photo = State()         # Ожидание фото для разметки
    choose_function_photo = State()     # Ожидание выбора функции обработки фото
    align_function_photo = State()      # Ожидание необходимости выравнивания значков
    yes_or_no = State()                 # Ожидание выбора полноты коллекции
    all_collection_create = State()     # Ожидание ввода названия коллекции после нарезки


class CollectionStates(StatesGroup):
    """
    Состояния при обработке коллекции и его редактировании
    """
    collections = State()                   # Ожидание выбора действия над коллекциями
    favorites = State()                     # Ожидание выбора действия над избранными коллекциями
    waiting_for_zip_create = State()        # Ожидание архива при создании коллекции
    waiting_for_zip_add = State()           # Ожидание архива при пополнении коллекции
    add_new_collection_zip_name = State()   # Ожидание ввода названия коллекции из архива
    waiting_for_name_collection = State()   # Ожидание ввода названия коллекции при переименовании
    state_null_badges = State()             # Выгрузка PDF файла с недостающими значками
