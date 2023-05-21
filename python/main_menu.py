import telebot
from bot_config import db, collection, bot
from telebot import types
import transactions
import registration
import re
@bot.message_handler(commands=['mm'])
def main_menu_func(message):
    if not collection.find_one({'chat_id': message.chat.id, 'confirmed': True}):
        bot.send_message(message.chat.id, 'У вас нет доступа к этой команде!')
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    people_button = types.KeyboardButton('Люди')
    organizations_button = types.KeyboardButton('Организации')
    about_me_button = types.KeyboardButton('О себе')
    if collection.find_one({'chat_id': message.chat.id, 'admin': 1}):
        about_me_button = types.KeyboardButton('Команды')
    markup.add(people_button, organizations_button, about_me_button)
    bot.send_message(message.chat.id, 'Выберите действие:', reply_markup=markup)

# ------------ПЕРЕВОДЫ ЧАСТНЫМ КЛИЕНТАМ-------------------------------#
@bot.message_handler(func=lambda message: message.text == 'Люди')
def start(message):
    # выводим все группы в базе данных
    if not collection.find_one({'chat_id': message.chat.id, 'confirmed': True}):
        bot.send_message(message.chat.id, 'У вас нет доступа к этой команде!')
        return
    groups = collection.distinct("group")
    markup = telebot.types.InlineKeyboardMarkup()
    for group in groups:
        markup.add(telebot.types.InlineKeyboardButton(text=group, callback_data=f"group:{group}"))
    bot.send_message(message.chat.id, "Выберите группу:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.split(":")[0] == "group") # Выбор группы
def handle_group_selection(call):
    # получаем название группы из callback_data
    group = call.data.split(":")[1]
    # получаем всех пользователей в группе, у которых admin != 1
    users = collection.find({"group": group, "admin": {"$ne": 1}, "chat_id": {"$ne": call.message.chat.id}})
    # создаем клавиатуру с именами пользователей
    markup = telebot.types.InlineKeyboardMarkup()
    for user in users:
        markup.add(telebot.types.InlineKeyboardButton(text=user["name"], callback_data=f"user:{user['chat_id']}"))
    # отправляем сообщение с клавиатурой
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"Вы выбрали {group} отряд.\nВыберите пользователя:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.split(":")[0] == "user") # Выбор пользователя
def handle_user_selection(call):
    # получаем id пользователя из callback_data
    user_id = call.data.split(":")[1]
    # получаем данные пользователя
    user = collection.find_one({"chat_id": int(user_id)})
    print(user['name'])
    # отправляем сообщение с информацией о пользователе
    if user is not None:
        keyboard = types.InlineKeyboardMarkup()
        callback_button = types.InlineKeyboardButton(text="✅Подтвердить", callback_data=f"transaction:{call.message.chat.id}:{user_id}")
        print(f"transaction:{call.message.chat.id}:{user_id}")
        keyboard.add(callback_button)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f"Вы планируете совершить перевод клиенту:\nИмя: {user['name']}\nОтряд: {user['group']}\n", reply_markup=keyboard)
    else:
        bot.answer_callback_query(callback_query_id=call.id, text="Пользователь не найден")

# ------------РАБОТА ОРГАНИЗАЦИЙ-------------------------------#

@bot.message_handler(func=lambda message: message.text == 'Организации')
def organizations_handler(message):
    if not collection.find_one({'chat_id': message.chat.id, 'confirmed': True}):
        bot.send_message(message.chat.id, 'У вас нет доступа к этой команде!')
        return
    org = db['organizations']
    if collection.find_one({'chat_id': message.chat.id, 'admin': 1}):
        if not org.find_one({'admin_chat_id': message.chat.id}):
            keyboard = types.InlineKeyboardMarkup()
            callback_button = types.InlineKeyboardButton(text="Мутим💪", callback_data=f"registration")
            keyboard.add(callback_button)
            bot.send_message(chat_id=message.chat.id, text=f"За вами🫵 не числится организации, мутим?🤔\n", reply_markup=keyboard)
        else:
            organizations_doc = org.find_one({'admin_chat_id': message.chat.id})
            org_id = organizations_doc['id_organization']
            keyboard = types.InlineKeyboardMarkup()
            callback_button1 = types.InlineKeyboardButton(text="🏛 Перевод организациям",
                                                         callback_data=f"start_orgorg:{org_id}")
            callback_button2 = types.InlineKeyboardButton(text="☺️ Перевод частным лицам",
                                                          callback_data=f"orgfiz:{org_id}")
            callback_button3 = types.InlineKeyboardButton(text="🗿 Об организации",
                                                          callback_data=f"orgabout:{org_id}")
            callback_button4 = types.InlineKeyboardButton(text="🥲 Запрос денег у частных лиц",
                                                          callback_data=f"query_money:{org_id}")
            keyboard.add(callback_button1)
            keyboard.add(callback_button2)
            keyboard.add(callback_button4)
            keyboard.add(callback_button3)
            bot.send_message(message.chat.id, text=f"Выберите действия с организацией",reply_markup=keyboard)
    else:
        groups = org.distinct("name")
        markup = telebot.types.InlineKeyboardMarkup()
        for group in groups:
            group_doc = org.find_one({'name': group})
            markup.add(telebot.types.InlineKeyboardButton(text=group, callback_data=f"fizorg:{group_doc['id_organization']}"))
        bot.send_message(message.chat.id, "Выберите группу:", reply_markup=markup)
        return
@bot.callback_query_handler(func=lambda call: call.data.split(":")[0] == "orgabout")
def orgaa(call):
    org = db['organizations']
    org_doc = org.find_one({'id_organization':call.data.split(":")[1]})
    bot.send_message(call.message.chat.id, f"Ваша организация \"{org_doc['name']}\"\n Баланс: {org_doc['balance']} буб.")

@bot.callback_query_handler(func=lambda call: call.data.split(":")[0] == "registration") # Регистрация организации
def org_reg_start(call):
    chat_id = call.message.chat.id
    sent = bot.send_message(chat_id,
                     'Для регистрации введите данные организации через запятую:\n\nФормат: "Название", "Уставной капитал"')
    bot.register_next_step_handler(sent, org_reg)
# хэндлер для кнопки "О себе"

def org_reg(message):
    organizations = db['organizations']
    chat_id = message.chat.id
    org_id = f"org{find_highest_org_id() + 1}"
    try:
        name, balance = message.text.split(',')
        balance = int(balance)
        if len(name) > 24:
            print(len(name))
            bot.send_message(message.chat.id, 'Максимум 23 символа')
            return
    except ValueError:
        if message.text == "Назад":
            bot.send_message(message.chat.id, 'Вернемся в главное меню')
            main_menu_func(message)
            return
        print('ValueError',message.text)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        people_button = types.KeyboardButton('Назад')
        markup.add(people_button)
        sent = bot.send_message(chat_id, '🌚 Неверный формат ввода! Попробуйте снова.', reply_markup=markup)
        bot.register_next_step_handler(message, org_reg)
        return

    organizations.insert_one({'id_organization': org_id,  'balance': balance, 'name': name.strip(),'admin_chat_id':chat_id})
    sent = bot.send_message(chat_id, 'Организация зарегистрированна')
    bot.register_next_step_handler(sent, main_menu_func)

def find_highest_org_id():
    highest_num = 0
    organizations = db['organizations']
    for doc in organizations.find():
        org_id = doc.get("id_organization")
        if org_id.startswith("org") and org_id[3:].isdigit():
            num = int(org_id[3:])
            if num > highest_num:
                highest_num = num
    return highest_num

#------------------------------------------------------------------------------------------------------------------------#
@bot.message_handler(func=lambda message: message.text == 'О себе')
def about_me_handler(message):
    if not collection.find_one({'chat_id': message.chat.id, 'confirmed': True}):
        bot.send_message(message.chat.id, f'Ваш id {message.chat.id}')
        return
    user = collection.find_one({"chat_id": message.chat.id})
    bot.send_message(message.chat.id, f"🧸 Ваше имя: {user['name']}\n🐒 Ваш отряд: {user['group']}\n💰 Ваш баланс: {user['balance']} Бублей")

@bot.message_handler(func=lambda message: message.text == 'Команды')
def admin_commands(message):
    bot.send_message(message.chat.id, f'Посмотреть балансы всего отряда\n/group <номер отряда>\nУстановить равный баланс в отряде\n/set_balance <номер группы> <сумма>\nУстановить баланс по id\n/set_id <id> <сумма>\nРегистрация детей из твоего отряда. Одного или через запятую\n/reg, <Имя Фамилия>\nзапятую после /reg обязательно\nУстановить соответствие между Именем и id(показывается в боте без регистрации)\n/compare <chat_id> <Имя> <Фамилия>"')

@bot.message_handler(commands=['group'])
def group_handler(message):
    # проверяем наличие номера группы в сообщении
    try:
        group_num = message.text.split()[1]
    except IndexError:
        bot.send_message(message.chat.id, "Вы не указали номер группы. Используйте команду в формате")
        bot.send_message(message.chat.id, "/group <номер группы>")# получаем список пользователей нужной группы
        return
    users = collection.find({'group': group_num})
    # формируем текст сообщения с именами и балансами пользователей
    text = f"{group_num}-й отряд:\n"
    for user in users:
        text += f"{user['name']}: {user['balance']}\n"
    # отправляем сообщение пользователю
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['set_balance'])
def set_balance(message):
    try:
        group_number, balance = message.text.split()[1:]
        group_number = int(group_number)
        balance = int(balance)
    except ValueError:
        bot.reply_to(message, "Неверный формат команды!")
        bot.send_message(message.chat.id, "/set_balance <номер группы> <сумма>")
        return

    collection.update_many({"group": group_number}, {"$set": {"balance": balance}})  # Установка баланса всем пользователям группы

    bot.reply_to(message, f"Баланс всех пользователей группы {group_number} установлен на {balance}")

@bot.message_handler(commands=['set_id'])
def set_balance_by_id(message):
    # получаем id пользователя и новый баланс из сообщения
    try:
        chat_id, new_balance = message.text.split()[1:]
        chat_id = int(chat_id)
        new_balance = int(new_balance)
    except ValueError:
        bot.reply_to(message, "Неверный формат команды!")
        bot.send_message(message.chat.id, "/set_id <id ребенка> <сумма>")
        return
    # обновляем баланс пользователя в базе данных
    result = collection.update_one({'chat_id': chat_id}, {'$set': {'balance': new_balance}})
    # проверяем, был ли найден пользователь и обновлен его баланс
    doc = collection.find_one({'chat_id': chat_id})
    if result.matched_count > 0:
        bot.send_message(message.chat.id, f"Баланс пользователя {doc['name']} обновлен до {new_balance} Бублей")
        bot.send_message(doc['chat_id'], f" 💸 Ваш баланс обновлен до {new_balance} Бублей")
    else:
        bot.send_message(message.chat.id, f"Пользователь с id {chat_id} не найден")

@bot.message_handler(commands=['reg,'])
def reg_handler(message):
    # получаем список имен из сообщения
    try:
        # Получаем имена пользователей из сообщения
        names = message.text.split(',')[1:]
        if not names:
            bot.send_message(message.chat.id, "Укажите хотя бы одно имя после команды /reg")
            return
    except IndexError:
        bot.send_message(message.chat.id, "Укажите хотя бы одно имя после команды /reg")
        return
    # получаем максимальный chat_id среди пользователей с chat_id < 10000
    doc = collection.find_one({'chat_id': {'$lt': 10000}}, {'chat_id': 1}, sort=[('chat_id', -1)])
    if doc:
        max_chat_id = doc['chat_id']
    else:
        max_chat_id = 0

    # добавляем новых пользователей в базу данных
    admin_doc = collection.find_one({'chat_id': message.chat.id})
    admin_group = admin_doc['group']
    for name in names:
        if name != "":
            user = {
                'chat_id': max_chat_id + 1,
                'name': name,
                'group': admin_group,
                'admin': 0,
                'confirmed': True,
                'balance': 0
            }
            db.users.insert_one(user)
            max_chat_id += 1
    # отправляем сообщение пользователю
    bot.send_message(message.chat.id, f"Пользователи {', '.join(names)} добавлены в базу данных.")


@bot.message_handler(commands=['compare'])
def compare_handler(message):
    # получаем имя и chat_id пользователя из сообщения
    if message.text.count(' ') < 3:
        print(message.text.count(' '))
        bot.send_message(message.chat.id, "Некорректный формат команды. Используйте /compare <chat_id> <Имя> <Фамилия>")
        return

    try:
        # получаем имя и chat_id из сообщения
        chat_id = message.text.split(' ')[1]
        name = message.text.split(' ')[2] + ' ' + message.text.split(' ')[3]
        print(name)
    except ValueError:
        bot.send_message(message.chat.id, "Некорректный формат команды. Используйте /compare <chat_id> <Имя> <Фамилия>")
        return

    # ищем пользователя в коллекции по имени
    user = collection.find_one({'name': name})
    if user is None:
        bot.send_message(message.chat.id, f"Пользователь с именем {name} не найден")
        return

    # обновляем chat_id пользователя
    result = collection.update_one({'_id': user['_id']}, {'$set': {'chat_id': int(chat_id)}})

    if result.modified_count == 1:
        bot.send_message(message.chat.id, f"Пользователю {name} успешно присвоен chat_id {chat_id}")
    else:
        bot.send_message(message.chat.id, "Ошибка при изменении chat_id")

if __name__ == "__main__":
    bot.polling(non_stop=True)