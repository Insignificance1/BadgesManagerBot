from aiogram import Bot, Dispatcher
from bot.settings import config
from database.db import DataBase
from model.detection import Detector
from concurrent.futures import ThreadPoolExecutor

bot = Bot(token=config.TOKEN)
dp = Dispatcher()
segmenter = Detector(model_path='../../v3-965photo-100ep.pt')
db = DataBase()
executor = ThreadPoolExecutor()
