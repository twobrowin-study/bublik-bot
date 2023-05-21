import telebot
# import telegram
from telebot import types
from datetime import datetime
from bot_config import client, db, collection, bot
from main_menu import main_menu_func
users = db['users']
transactions = db['transactions']

#-------------------------------ТРАНЗАКЦИИ МЕЖДУ КЛИЕНТАМИ--------------------------------------#
@bot.callback_query_handler(func=lambda call: call.data.startswith('transaction:'))
def process_transaction_callback(call):
    # Запрашиваем у пользователя сумму транзакции
    print(call.data)
    amount_message = bot.send_message(call.message.chat.id, 'Введите сумму транзакции:')
    # Устанавливаем состояние пользователя в 'waiting_for_amount'
    bot.register_next_step_handler(amount_message, process_amount_callback, call.data)
def process_amount_callback(message, callback_data):
    print(callback_data)
    try:
        amount = int(message.text)
    except ValueError:
        if message.text == "Назад":
            bot.send_message(message.chat.id, 'Вернемся в главное меню')
            main_menu_func(message)
            return
        print('ValueError',message.text)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        people_button = types.KeyboardButton('Назад')
        markup.add(people_button)
        sent = bot.send_message(message.chat.id, '🙈 Неверный формат ввода! Попробуйте снова.🙉', reply_markup=markup)
        bot.register_next_step_handler(sent, process_amount_callback, callback_data)
        return

    parts = callback_data.split(':')
    sender = int(parts[1])
    recipient = int(parts[2])
    print(sender, recipient)
    # Находим пользователя-отправителя и получателя
    recipient_doc = users.find_one({'chat_id': int(recipient)})
    keyboard = types.InlineKeyboardMarkup()
    callback_button = types.InlineKeyboardButton(text="✅ Подтвердить",
                                                 callback_data=f"transaction_with_sum:{sender}:{recipient}:{amount}")
    keyboard.add(callback_button)
    bot.send_message(chat_id=message.chat.id, text=f"Вы планируете совершить перевод клиенту:\n{recipient_doc['name']} из {recipient_doc['group']}-го отряда.\nСумма перевода: {amount} Бублей\n", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith('transaction_with_sum:'))
def process_transaction(call):
    # Разделяем callback_data на составляющие
    users = db['users']
    parts = str(call.data).split(':')
    print(parts)
    sender = int(parts[1])
    recipient = int(parts[2])
    amount = int(parts[3])
    # Находим пользователя-отправителя и получателя
    sender_doc = users.find_one({'chat_id': sender})
    recipient_doc = users.find_one({'chat_id': recipient})
    # Проверяем, что пользователи найдены
    if not sender_doc:
        return 'Отправитель не найден'
    if not recipient_doc:
        return 'Получатель не найден'
    # Проверяем, что сумма транзакции не превышает баланс отправителя
    print(sender, recipient, amount)
    if sender_doc['balance'] < amount:
        sent = bot.send_message(sender_doc['chat_id'], 'Недостаточно средств 🥲')
        return 'Недостаточно средств '


    # Обновляем балансы пользователей
    users.update_one({'chat_id': sender}, {'$inc': {'balance': -amount}})
    users.update_one({'chat_id': recipient}, {'$inc': {'balance': amount}})

    # Добавляем новую транзакцию
    transaction = {
        'sender': sender,
        'recipient': recipient,
        'amount': amount,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    transactions.insert_one(transaction)
    recipient_doc = users.find_one({'chat_id': recipient})
    try:
        bot.send_message(recipient_doc['chat_id'], f" 💸 Вам поступил перевод {amount} Бублей от {sender_doc['name']} из {sender_doc['group']}-го отряда\n💰 Ваш баланс: {recipient_doc['balance']} Бублей")
    except:
        return
    bot.send_message(sender_doc['chat_id'], '✅ Транзакция успешно проведена')
    return 'Транзакция успешно проведена'

# --------------------------------------------ПЕРЕВОД ОТ ОРГАНИЗАЦИИ КЛИЕНТУ-----------------------------------------------------------------------------------------------------------

@bot.callback_query_handler(func=lambda call: call.data.startswith('orgfiz:'))
def start_org(call):
    groups = collection.distinct("group")
    org_id = call.data.split(":")[1]
    markup = telebot.types.InlineKeyboardMarkup()
    for group in groups:
        markup.add(telebot.types.InlineKeyboardButton(text=group, callback_data=f"group_org:{group}:{org_id}"))
    bot.send_message(call.message.chat.id, "Выберите отряд:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.split(":")[0] == "group_org")
def handle_group_selection_org(call):
    # получаем название группы из callback_data
    group = call.data.split(":")[1]
    org_id = call.data.split(":")[2]
    # получаем всех пользователей в группе, у которых admin != 1
    users = collection.find({"group": group, "admin": {"$ne": 1}})
    # создаем клавиатуру с именами пользователей
    markup = telebot.types.InlineKeyboardMarkup()
    for user in users:
        markup.add(telebot.types.InlineKeyboardButton(text=user["name"], callback_data=f"user_org:{org_id}:{user['chat_id']}"))
    # отправляем сообщение с клавиатурой
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"Вы выбрали {group} отряд.\nВыберите пользователя:", reply_markup=markup)

# обработчик выбора пользователя
@bot.callback_query_handler(func=lambda call: call.data.split(":")[0] == "user_org")
def handle_user_selection_org(call):
    # получаем id пользователя из callback_data
    org_id = call.data.split(":")[1]
    user_id = call.data.split(":")[2]
    # получаем данные пользователя
    user = collection.find_one({"chat_id": int(user_id)})
    # отправляем сообщение с информацией о пользователе
    if user is not None:
        keyboard = types.InlineKeyboardMarkup()
        callback_button = types.InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"transaction_org:{org_id}:{user_id}")
        keyboard.add(callback_button)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f"Вы планируете совершить перевод клиенту со счета компании:\nИмя: {user['name']}\nОтряд: {user['group']}\n", reply_markup=keyboard)
    else:
        bot.answer_callback_query(callback_query_id=call.id, text="Пользователь не найден")



@bot.callback_query_handler(func=lambda call: call.data.startswith('transaction_org'))
def process_transaction_callback_org(call):
    # Запрашиваем у пользователя сумму транзакции
    amount_message = bot.send_message(call.message.chat.id, 'Введите сумму транзакции:')
    # Устанавливаем состояние пользователя в 'waiting_for_amount'
    bot.register_next_step_handler(amount_message, process_amount_callback_org, call.data)
def process_amount_callback_org(message, callback_data):
    # Получаем сумму транзакции из сообщения пользователя
    try:
        amount = int(message.text)
    except ValueError:
        if message.text == "Назад":
            bot.send_message(message.chat.id, 'Вернемся в главное меню')
            main_menu_func(message)
            return
        print('ValueError', message.text)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        people_button = types.KeyboardButton('Назад')
        markup.add(people_button)
        sent = bot.send_message(chat_id, '🗿 Неверный формат ввода! Попробуйте снова.', reply_markup=markup)
        bot.register_next_step_handler(sent, process_amount_callback_org, callback_data)
        return

    parts = callback_data.split(':')
    sender = parts[1]
    recipient = int(parts[2])
    # Находим пользователя-отправителя и получателя
    recipient_doc = users.find_one({'chat_id': recipient})
    keyboard = types.InlineKeyboardMarkup()
    callback_button = types.InlineKeyboardButton(text="✅ Подтвердить",
                                                 callback_data=f"transaction_sum_org:{sender}:{recipient}:{amount}")
    keyboard.add(callback_button)
    bot.send_message(chat_id=message.chat.id, text=f"Вы планируете совершить перевод клиенту со счета организации:\n{recipient_doc['name']} из {recipient_doc['group']}-го отряда.\nСумма перевода: {amount} Бублей\n", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith('transaction_sum_org:'))
def process_transaction_org(call):
    # Разделяем callback_data на составляющие
    org = db['organizations']
    parts = str(call.data).split(':')
    print(parts)
    sender = parts[1]
    recipient = int(parts[2])
    amount = int(parts[3])

    # Находим пользователя-отправителя и получателя
    sender_doc = org.find_one({'id_organization': sender})
    recipient_doc = users.find_one({'chat_id': recipient})
    # Проверяем, что пользователи найдены
    if not sender_doc:
        return 'Отправитель не найден'
    if not recipient_doc:
        return 'Получатель не найден'
    # Проверяем, что сумма транзакции не превышает баланс отправителя
    if sender_doc['balance'] < amount:
        sent = bot.send_message(sender_doc['admin_chat_id'], 'Недостаточно средств')
        main_menu_func(message)
        return 'Недостаточно средств'
    tax = int(amount*0.13)
    # Обновляем балансы пользователей
    org.update_one({'id_organization': sender}, {'$inc': {'balance': -(amount+tax)}})
    org.update_one({'id_organization': "org0"}, {'$inc': {'balance': tax}})
    users.update_one({'chat_id': recipient}, {'$inc': {'balance': amount}})
    # Добавляем новую транзакцию
    transaction = {
        'sender': sender,
        'recipient': recipient,
        'amount': amount,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    transactions.insert_one(transaction)
    recipient_doc = users.find_one({'chat_id': recipient})
    bot.send_message(sender_doc['admin_chat_id'], f'✅ Транзакция успешно проведена, удержан налог {tax} Бублей')
    try:
        bot.send_message(recipient_doc['chat_id'], f"💸 Вам поступил перевод {amount} Бублей от {sender_doc['name']}\nВаш баланс: {recipient_doc['balance']}")
    except:
        return
    return 'Транзакция успешно проведена'


# -------------------------------ТРАНЗАКЦИИ ОТ КЛИЕНТА ОРГАНИЗАЦИИ----------------------------------------------------------------

@bot.callback_query_handler(func=lambda call: call.data.startswith('fizorg'))
def process_transaction_callback_org(call):
    # Запрашиваем у пользователя сумму транзакции
    amount_message = bot.send_message(call.message.chat.id, 'Введите сумму транзакции:')
    # Устанавливаем состояние пользователя в 'waiting_for_amount'
    bot.register_next_step_handler(amount_message, process_amount_callback_org_p, call.data)
def process_amount_callback_org_p(message, callback_data):
    # Получаем сумму транзакции из сообщения пользователя
    try:
        amount = int(message.text)
    except ValueError:
        if message.text == "Назад":
            bot.send_message(message.chat.id, 'Вернемся в главное меню')
            main_menu_func(message)
            return
        print('ValueError', message.text)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        people_button = types.KeyboardButton('Назад')
        markup.add(people_button)
        sent = bot.send_message(message.chat.id, 'Неверный формат ввода! Попробуйте снова.', reply_markup=markup)
        bot.register_next_step_handler(sent, process_amount_callback_org_p, callback_data)
        return
    orga = db['organizations']
    parts = callback_data.split(':')
    sender = message.chat.id
    recipient = parts[1]
    # Находим пользователя-отправителя и получателя
    recipient_doc = orga.find_one({'id_organization': recipient})
    org_id = recipient_doc['id_organization']
    sender_doc = collection.find_one({'chat_id':message.chat.id})

    keyboard = types.InlineKeyboardMarkup()
    callback_button = types.InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"t:{sender}:{org_id}:{amount}")
    keyboard.add(callback_button)
    bot.send_message(chat_id=message.chat.id, text=f"Вы планируете совершить перевод организации: {recipient_doc['name']}\nСумма перевода: {amount} буб\n", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith('t:'))
def process_transaction_org_r(call):
    # Разделяем callback_data на составляющие
    org = db['organizations']
    parts = str(call.data).split(':')
    print(parts)
    sender = int(parts[1])
    recipient = parts[2]
    amount = int(parts[3])

    # Находим пользователя-отправителя и получателя
    sender_doc = users.find_one({'chat_id': sender})
    recipient_doc = org.find_one({'id_organization': recipient})
    # Проверяем, что пользователи найдены
    if not sender_doc:
        return 'Отправитель не найден'
    if not recipient_doc:
        return 'Получатель не найден'
    # Проверяем, что сумма транзакции не превышает баланс отправителя
    if sender_doc['balance'] < amount:
        bot.send_message(sender, 'Недостаточно средств')
        return 'Недостаточно средств'
        # bot.register_next_step_handler(sent, process_transaction_org, call)
    # Обновляем балансы пользователей
    tax = int(0.2*amount)
    users.update_one({'chat_id': sender}, {'$inc': {'balance': -amount}})
    org.update_one({'id_organization': recipient}, {'$inc': {'balance': (amount - tax)}})
    org.update_one({'id_organization': "org0"}, {'$inc': {'balance': (amount - tax)}})

    # Добавляем новую транзакцию
    transaction = {
        'sender': sender,
        'recipient': recipient,
        'amount': amount,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    transactions.insert_one(transaction)
    recipient_doc = org.find_one({'id_organization': recipient})
    try:
        bot.send_message(recipient_doc['admin_chat_id'], f"💸 В компанию поступил перевод {amount} буб от {sender_doc['name']} из {sender_doc['group']}-го отряда, удержан налог {tax} Бублей\n💰 Счет компании: {recipient_doc['balance']}")
    except:
        return
    bot.send_message(sender_doc['chat_id'], '✅ Транзакция успешно проведена')
    return 'Транзакция успешно проведена'


#-------------------------------------------ТРАНЗАКЦИИ ОТ ОРГАНИЗАЦИИ ОРГАНИЗАЦИИ-----------------------------------------------------------p


@bot.callback_query_handler(func=lambda call: call.data.startswith('start_orgorg:'))
def orgorg(call):
    org = db['organizations']
    org_id = call.data.split(":")[1]
    groups = org.distinct("name")

    markup = telebot.types.InlineKeyboardMarkup()

    for group in groups:
        group_doc = org.find_one({'name':group})
        markup.add(telebot.types.InlineKeyboardButton(text=group, callback_data=f"orgorg:{org_id}:{group_doc['id_organization']}"))
    bot.send_message(call.message.chat.id, "Выберите группу:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('orgorg:'))
def process_transaction_callback_orgorg(call):
    # Запрашиваем у пользователя сумму транзакции
    amount_message = bot.send_message(call.message.chat.id, 'Введите сумму транзакции:')
    # Устанавливаем состояние пользователя в 'waiting_for_amount'
    bot.register_next_step_handler(amount_message, process_amount_callback_orgorg, call.data)

def process_amount_callback_orgorg(message, callback_data):
    # Получаем сумму транзакции из сообщения пользователя
    try:
        amount = int(message.text)
    except ValueError:
        if message.text == "Назад":
            bot.send_message(message.chat.id, 'Вернемся в главное меню')
            main_menu_func(message)
            return
        print('ValueError', message.text)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        people_button = types.KeyboardButton('Назад')
        markup.add(people_button)
        sent = bot.send_message(message.chat.id, 'Неверный формат ввода! Попробуйте снова.', reply_markup=markup)
        bot.register_next_step_handler(sent, process_amount_callback_orgorg, callback_data)
        return
    org = db['organizations']
    parts = callback_data.split(':')
    sender = parts[1]
    recipient = parts[2]
    # Находим пользователя-отправителя и получателя
    sender_doc = org.find_one({'id_organization': sender})
    recipient_doc = org.find_one({'id_organization': recipient})
    recipient = recipient_doc['id_organization']

    keyboard = types.InlineKeyboardMarkup()
    callback_button = types.InlineKeyboardButton(text="✅ Подтвердить",callback_data=f"tra_orgorg:{sender}:{recipient}:{amount}")
    keyboard.add(callback_button)
    bot.send_message(chat_id=message.chat.id, text=f"Вы планируете совершить перевод организации {recipient_doc['name']} со счета своей организации\nСумма перевода: {amount} Бублей\n", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith('tra_orgorg:'))
def process_transaction_orgorg(call):
    # Разделяем callback_data на составляющие
    org = db['organizations']
    parts = call.data.split(':')
    print(parts)
    sender = parts[1]
    recipient = parts[2]
    amount = int(parts[3])
    # Находим пользователя-отправителя и получателя
    sender_doc = org.find_one({'id_organization': sender})
    recipient_doc = org.find_one({'id_organization': recipient})
    print(sender_doc)
    # Проверяем, что пользователи найдены
    if not sender_doc:
        return 'Отправитель не найден'
    if not recipient_doc:
        return 'Получатель не найден'
    # Проверяем, что сумма транзакции не превышает баланс отправителя
    if sender_doc['balance'] < amount:
        sent = bot.send_message(sender_doc['admin_chat_id'], 'Недостаточно средств')
        return 'Недостаточно средств'
    # Обновляем балансы пользователей
    re_be = recipient_doc['balance']
    se_be = sender_doc['balance']

    org.update_one({'id_organization': sender}, {'$inc': {'balance': -amount}})
    org.update_one({'id_organization': recipient}, {'$inc': {'balance': amount}})

    sender_doc = org.find_one({'id_organization': sender})
    recipient_doc = org.find_one({'id_organization': recipient})

    se_af = sender_doc['balance']
    re_af = recipient_doc['balance']

    print(re_be, se_be, re_af, se_af)

    # Добавляем новую транзакцию
    transaction = {
        'sender': sender,
        'recipient': recipient,
        'amount': amount,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    transactions.insert_one(transaction)
    try:
        bot.send_message(recipient_doc['admin_chat_id'], f"💸 В компанию поступил перевод {amount} Бублей от \"{sender_doc['name']}\"\n💰 Счет компании: {recipient_doc['balance']}")
    except:
        return
    bot.send_message(sender_doc['admin_chat_id'], '✅ Транзакция успешно проведена')
    return 'Транзакция успешно проведена'



#--------------------------------ЗАПРОС ДЕНЕГ У ПЕЗДЮКОВ-----------------------------


@bot.callback_query_handler(func=lambda call: call.data.startswith('query_money:'))
def start_q(call):
    groups = collection.distinct("group")
    org_id = call.data.split(":")[1]
    markup = telebot.types.InlineKeyboardMarkup()
    for group in groups:
        markup.add(telebot.types.InlineKeyboardButton(text=group, callback_data=f"group_q:{group}:{org_id}"))
    bot.send_message(call.message.chat.id, "Выберите отряд:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.split(":")[0] == "group_q")
def handle_group_selection_q(call):
    # получаем название группы из callback_data
    group = call.data.split(":")[1]
    org_id = call.data.split(":")[2]
    # получаем всех пользователей в группе, у которых admin != 1
    users = collection.find({"group": group, "admin": {"$ne": 1}})
    # создаем клавиатуру с именами пользователей
    markup = telebot.types.InlineKeyboardMarkup()
    for user in users:
        markup.add(telebot.types.InlineKeyboardButton(text=user["name"], callback_data=f"user_q:{org_id}:{user['chat_id']}"))
    # отправляем сообщение с клавиатурой
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"Вы выбрали {group} отряд.\nВыберите пользователя:", reply_markup=markup)

# обработчик выбора пользователя
@bot.callback_query_handler(func=lambda call: call.data.split(":")[0] == "user_q")
def handle_user_selection_q(call):
    # получаем id пользователя из callback_data
    org_id = call.data.split(":")[1]
    user_id = call.data.split(":")[2]
    # получаем данные пользователя
    user = collection.find_one({"chat_id": int(user_id)})
    # отправляем сообщение с информацией о пользователе
    if user is not None:
        keyboard = types.InlineKeyboardMarkup()
        callback_button = types.InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"transaction_q:{org_id}:{user_id}")
        keyboard.add(callback_button)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f"Вы планируете запросить деньги у \nИмя: {user['name']}\nОтряд: {user['group']}\n", reply_markup=keyboard)
    else:
        bot.answer_callback_query(callback_query_id=call.id, text="Пользователь не найден")



@bot.callback_query_handler(func=lambda call: call.data.startswith('transaction_q'))
def process_transaction_callback_q(call):
    # Запрашиваем у пользователя сумму транзакции
    amount_message = bot.send_message(call.message.chat.id, 'Введите сумму транзакции:')
    # Устанавливаем состояние пользователя в 'waiting_for_amount'
    bot.register_next_step_handler(amount_message, process_amount_callback_q, call.data)
def process_amount_callback_q(message, callback_data):
    # Получаем сумму транзакции из сообщения пользователя
    try:
        amount = int(message.text)
    except ValueError:
        if message.text == "Назад":
            bot.send_message(message.chat.id, 'Вернемся в главное меню')
            main_menu_func(message)
            return
        print('ValueError', message.text)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        people_button = types.KeyboardButton('Назад')
        markup.add(people_button)
        sent = bot.send_message(chat_id, 'Неверный формат ввода! Попробуйте снова.', reply_markup=markup)
        bot.register_next_step_handler(sent, process_amount_callback_q, callback_data)
        return

    parts = callback_data.split(':')
    sender = parts[1]
    recipient = int(parts[2])
    # Находим пользователя-отправителя и получателя
    recipient_doc = users.find_one({'chat_id': recipient})
    keyboard = types.InlineKeyboardMarkup()
    callback_button = types.InlineKeyboardButton(text="Подтвердить",
                                                 callback_data=f"transaction_sum_q:{sender}:{recipient}:{amount}")
    keyboard.add(callback_button)
    bot.send_message(chat_id=message.chat.id, text=f"Вы планируете запросить бубли у \n{recipient_doc['name']} из {recipient_doc['group']}-го отряда.\nСумма перевода: {amount} Бублей\n", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith('transaction_sum_q:'))
def process_transaction_q(call):
    # Разделяем callback_data на составляющие
    org = db['organizations']
    parts = str(call.data).split(':')
    print(parts)
    sender = parts[1]
    recipient = int(parts[2])
    amount = int(parts[3])

    # Находим пользователя-отправителя и получателя
    sender_doc = org.find_one({'id_organization': sender})
    recipient_doc = users.find_one({'chat_id': recipient})
    # Проверяем, что пользователи найдены
    if not sender_doc:
        return 'Отправитель не найден'
    if not recipient_doc:
        return 'Получатель не найден'
    # Проверяем, что сумма транзакции не превышает баланс отправителя
    if recipient_doc['balance'] < amount:
        sent = bot.send_message(sender_doc['admin_chat_id'], 'У клиента недостаточно средств')
        main_menu_func(call.message)
        return 'Недостаточно средств'
    tax = int(amount*0.13)
    # Обновляем балансы пользователей
    org.update_one({'id_organization': sender}, {'$inc': {'balance': (amount-tax)}})
    org.update_one({'id_organization': "org0"}, {'$inc': {'balance': tax}})
    users.update_one({'chat_id': recipient}, {'$inc': {'balance': -amount}})
    # Добавляем новую транзакцию
    transaction = {
        'sender': recipient,
        'recipient': sender,
        'amount': amount,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    transactions.insert_one(transaction)
    recipient_doc = users.find_one({'chat_id': recipient})
    sender_doc = org.find_one({'id_organization': sender})
    bot.send_message(sender_doc['admin_chat_id'],
                     f"{amount} Бублей от {recipient_doc['name']} поступило на\nВаш баланс: {sender_doc['balance']} буб.\nБаланс {recipient_doc['name']} = {recipient_doc['balance']} буб.\nНалог составляет {tax} буб.")
    try:
        bot.send_message(recipient_doc['chat_id'], f"🏛 Оплата {amount} Бублей организации \"{sender_doc['name']}\"")
    except:
        return
    return 'Транзакция успешно проведена'

