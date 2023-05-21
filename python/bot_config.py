import telebot
import pymongo

from os import environ

client = pymongo.MongoClient(environ.get('MONGODB_CONNECTION'))
db = client["Bubli-Bank"]
collection = db["users"]
bot = telebot.TeleBot(environ.get('TELEGRAM_TOKEN'))
