import telebot
# import telegram
from telebot import types
from datetime import datetime
from bot_config import client, db, collection, bot

from os import environ

# подключение к базе данных MongoDB

# создание бота и его токена

#  https://t.me/BubliBank_bot?start=admin_reg
@bot.message_handler(commands = ['start'])
def user_registration(message):
    chat_id = message.chat.id
    print(message.text)
    # проверяем, есть ли пользователь в базе данных
    if message.text != f"/start {environ.get('ADMIN_STRING')}":
        if collection.find_one({'chat_id': chat_id}):
            bot.send_message(chat_id, 'Вы уже зарегестрированы!')
        else:
            sent = bot.send_message(chat_id,'Добро пожаловать в \n💰 Бубли-Банк 💰 \n- самый совершенный детский онлайн-банк в России. Для регистрации введите свои данные:\n\nФормат: Имя Фамилия, номер отряда(цифра)')
            bot.register_next_step_handler(sent, user_registration)

    else:
        if collection.find_one({'chat_id': chat_id}):
            bot.send_message(chat_id, 'Вы уже зарегистрированы как админ')
        else:
            sent = bot.send_message(chat_id,
                                    'Вау, админ? Мегахорош, давай данные и погнали рулить лучшим банком страны.💚\n\nФормат: Имя Фамилия, номер отряда(цифрой)')
            bot.register_next_step_handler(sent, admin_registration)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm'))
def confirm_registration(call):
    chat_id = call.message.chat.id
    # проверяем, является ли отправитель сообщения администратором
    if not collection.find_one({'chat_id': chat_id, 'admin': 1}):
        bot.send_message(chat_id, 'У вас нет доступа к этой команде!')
    else:
        # получаем chat_id пользователя, которого нужно подтвердить
        try:
            user_chat_id = int(call.data.split(':')[1])
        except (ValueError, IndexError):
            bot.send_message(chat_id, 'Неверный формат команды!')
            return
        # проверяем, существует ли пользователь с таким chat_id
        user = collection.find_one({'chat_id': user_chat_id})
        if not user:
            bot.send_message(chat_id, 'Пользователь не найден!')
        else:
            # подтверждаем регистрацию пользователя
            collection.update_one({'chat_id': user_chat_id}, {'$set': {'confirmed': True}})
            bot.send_message(user_chat_id, '✅Ваша регистрация подтверждена администратором✅\n Нажмите /mm для перехода в главное меню!')
            bot.send_message(chat_id, f'✅Регистрация пользователя {user["name"]} подтверждена!')


def admin_registration(message):
    chat_id = message.chat.id
    # проверяем, есть ли пользователь в базе данных
    if collection.find_one({'chat_id': chat_id}):
        bot.send_message(chat_id, 'Вы уже зарегистрированы!!!')
    else:
        # разбиваем текст на имя, фамилию и название группы
        try:
            name, group = message.text.split(',')
        except ValueError:
            sent = bot.send_message(chat_id, 'Неверный формат ввода! Попробуйте снова.')
            bot.register_next_step_handler(sent, admin_registration)
            return
        # проверяем, не зарегистрирован ли уже пользователь с таким именем
        if collection.find_one({'name': name}):
            bot.send_message(chat_id, 'Запись с вашим именем уже есть в БД')
        else:
            # сохраняем данные пользователя в базе данных
            collection.insert_one({'chat_id': chat_id, 'name': name.strip(), 'group': group.strip(), 'admin': 1, 'confirmed': True, 'balance': 0})
            bot.send_message(chat_id, '✅Регистрация успешно завершена, тыкай /mm для перехода в главное меню')



def user_registration(message):
    chat_id = message.chat.id
    # проверяем, есть ли пользователь уже зарегистрирован в базе данных
    if collection.find_one({'chat_id': chat_id}):
        bot.send_message(chat_id, 'Вы уже зарегистрирован!')
        return
    # разбиваем текст на имя и название группы
    try:
        name, group = message.text.split(',')
    except ValueError:
        sent = bot.send_message(chat_id, '🫤Неверный формат ввода! Попробуйте снова.')
        bot.register_next_step_handler(sent, user_registration)
        return
    # проверяем, не зарегистрирован ли уже пользователь с таким именем
    # сохраняем данные пользоватля в базе данных со статусом на подтверждении администратора
    collection.insert_one({'chat_id': chat_id, 'name': name.strip(), 'group': group.strip(), 'admin': 0,'confirmed': False, 'balance': 0})
    # отправляем данные на подтверждение администратору
    admin_list = collection.find({'group': group.strip(), 'admin': 1})
    print(admin_list)
    for admin in admin_list:
        message_text = f'🤔Подтвердите регистрацию нового пользователя:\n' \
                       f'Имя: {name}\n' \
                       f'Группа: {group}\n'
        keyboard = types.InlineKeyboardMarkup()
        callback_button = types.InlineKeyboardButton(text="✅Подтвердить", callback_data=f"confirm:{chat_id}")
        print(f"confirm:{chat_id}")
        keyboard.add(callback_button)
        bot.send_message(admin['chat_id'], text=message_text, reply_markup=keyboard)

    bot.send_message(chat_id, 'Данные отправлены на подтверждение администратору😏')

@bot.message_handler(commands=['delete'])
def delete_account(message):
    chat_id = message.chat.id
    # проверяем, есть ли запись с таким chat_id в базе данных
    user = collection.find_one({'chat_id': chat_id})
    if user:
        collection.delete_one({'chat_id': chat_id})
        bot.send_message(chat_id, "Ваша учетная запись удалена.")
    else:
        bot.send_message(chat_id, "У вас нет зарегистрированной учетной записи.")

@bot.message_handler(commands=['support'])
def support_command_handler(message):
    sent = bot.reply_to(message, f'Здравствуйте, @{message.from_user.username}! Если у вас есть какие-то вопросы или проблемы, пожалуйста, опишите их в следующем сообщении. В случае необходимости я свяжусь с IT-директором банка Федором Андреевичем Шалуповым')
    bot.register_next_step_handler(sent, save_to_mongo)
def save_to_mongo(message):
    collection = db['support']
    # Приводим дату сообщения к нормальному формату
    date = datetime.fromtimestamp(message.date).strftime('%Y-%m-%d %H:%M:%S')

    # Создаем словарь, в котором будем хранить информацию о сообщении
    message_data = {
        'text': message.text,
        'date': date,
        'from_user': message.from_user.username,
        'chat_id': message.chat.id,
        'processed': False,
        'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # Записываем сообщение в коллекцию
    collection.insert_one(message_data)
    bot.send_message(chat_id, "Сообщение сохранено в базе данных. Вы можете продолжать пользоваться ботом.")
