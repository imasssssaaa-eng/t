#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gift Cases Telegram Bot
Полный скрипт с токеном
"""

import telebot
from telebot import types
import sqlite3
from datetime import datetime

TOKEN = "8727248106:AAFJnQAHgcBf9B_qfCy4-EOkTGSZ0_Xa09Q"
bot = telebot.TeleBot(TOKEN)
user_states = {}
DB_PATH = 'gift_cases.db'

# ============================================
# DATABASE FUNCTIONS
# ============================================

def init_db():
    """Инициализация БД"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 0,
            total_spent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            amount INTEGER,
            type TEXT,
            status TEXT,
            payment_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS case_opens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            case_type TEXT,
            reward TEXT,
            amount_spent INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

def get_or_create_user(chat_id, username=None):
    """Получить или создать пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (chat_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute('''
            INSERT INTO users (telegram_id, username)
            VALUES (?, ?)
        ''', (chat_id, username))
        conn.commit()
    
    conn.close()
    return get_user_info(chat_id)

def get_user_info(chat_id):
    """Получить информацию о пользователе"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (chat_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_balance(chat_id):
    """Получить баланс пользователя"""
    user = get_user_info(chat_id)
    return user[2] if user else 0

def add_balance(chat_id, amount):
    """Добавить баланс пользователю"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users 
        SET balance = balance + ?, 
            total_spent = total_spent + ?,
            last_activity = CURRENT_TIMESTAMP
        WHERE telegram_id = ?
    ''', (amount, amount, chat_id))
    
    conn.commit()
    conn.close()

def deduct_balance(chat_id, amount):
    """Снять со счета"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT balance FROM users WHERE telegram_id = ?', (chat_id,))
    result = cursor.fetchone()
    
    if not result or result[0] < amount:
        conn.close()
        return False
    
    cursor.execute('''
        UPDATE users 
        SET balance = balance - ?,
            last_activity = CURRENT_TIMESTAMP
        WHERE telegram_id = ?
    ''', (amount, chat_id))
    
    conn.commit()
    conn.close()
    return True

def add_transaction(chat_id, amount, trans_type, status, payment_id=None):
    """Добавить запись о транзакции"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO transactions 
        (telegram_id, amount, type, status, payment_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (chat_id, amount, trans_type, status, payment_id))
    
    conn.commit()
    conn.close()

def get_user_transactions(chat_id, limit=20):
    """Получить историю транзакций"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, amount, type, status, created_at 
        FROM transactions 
        WHERE telegram_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (chat_id, limit))
    results = cursor.fetchall()
    conn.close()
    return results

def get_top_users(limit=10):
    """Получить топ пользователей"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT telegram_id, username, total_spent, balance 
        FROM users 
        ORDER BY total_spent DESC 
        LIMIT ?
    ''', (limit,))
    results = cursor.fetchall()
    conn.close()
    return results

def get_stats():
    """Получить статистику"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(total_spent) FROM users')
    total_revenue = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT SUM(balance) FROM users')
    total_balance = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM transactions WHERE type = "refill" AND status = "completed"')
    completed_refills = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_users': total_users,
        'total_revenue': total_revenue,
        'total_balance': total_balance,
        'completed_refills': completed_refills
    }

# ============================================
# BOT HANDLERS
# ============================================

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    username = message.from_user.username or message.from_user.first_name
    
    get_or_create_user(chat_id, username)
    user_states[chat_id] = 'main'
    
    text = """Добро пожаловать в Gift Cases!

Открывай кейсы, улучшай NFT-подарки и забирай призы прямо в Telegram.

🎁 Кейсы — выбивай топовые NFT-подарки

Начни с кейса или попробуй апгрейд прямо сейчас!"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎮 Играть", url="http://t.me/gift_pepe_bot/gift"))
    markup.add(types.InlineKeyboardButton("⭐ Пополнить", callback_data="refill"))
    markup.add(types.InlineKeyboardButton("💰 Баланс", callback_data="balance"))
    
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "balance")
def show_balance(call):
    chat_id = call.message.chat.id
    balance = get_balance(chat_id)
    
    text = f"""💰 Ваш баланс

Текущий баланс: <b>{balance} ⭐</b>

Используйте кнопку "Пополнить" для добавления звезд."""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⭐ Пополнить", callback_data="refill"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back"))
    
    bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "refill")
def refill_menu(call):
    chat_id = call.message.chat.id
    user_states[chat_id] = 'refill'
    
    text = """💳 Пополнение Баланса

Автоматически введите сумму вашего пополнения (ваше пополнение автоматчески зачислиться на веб сайте)

Пополнение происходит в валюте <b>Звездах ⭐</b>

<i>Минимум: 1 ⭐
Максимум: 10000 ⭐</i>"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back"))
    
    bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back")
def back_to_main(call):
    chat_id = call.message.chat.id
    user_states[chat_id] = 'main'
    
    text = """Добро пожаловать в Gift Cases!

Открывай кейсы, улучшай NFT-подарки и забирай призы прямо в Telegram.

🎁 Кейсы — выбивай топовые NFT-подарки

Начни с кейса или попробуй апгрейд прямо сейчас!"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎮 Играть", url="http://t.me/gift_pepe_bot/gift"))
    markup.add(types.InlineKeyboardButton("⭐ Пополнить", callback_data="refill"))
    markup.add(types.InlineKeyboardButton("💰 Баланс", callback_data="balance"))
    
    bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'refill')
def process_refill_amount(message):
    chat_id = message.chat.id
    
    try:
        amount = int(message.text)
        
        if amount <= 0:
            bot.send_message(chat_id, "❌ Сумма должна быть больше 0")
            return
        
        if amount > 10000:
            bot.send_message(chat_id, "❌ Максимальная сумма: 10000 ⭐")
            return
        
        payment_id = f"giftcases_refill_{chat_id}_{int(datetime.now().timestamp())}"
        add_transaction(chat_id, amount, 'refill', 'pending', payment_id)
        
        prices = [types.LabeledPrice(label="Пополнение баланса", amount=amount)]
        
        bot.send_invoice(
            chat_id=chat_id,
            title="Пополнение баланса Gift Cases",
            description=f"Пополнение на {amount} ⭐",
            invoice_payload=payment_id,
            provider_token="",
            currency="XTR",
            prices=prices,
            start_parameter=f"refill_{amount}"
        )
        
        user_states[chat_id] = 'main'
        
    except ValueError:
        bot.send_message(chat_id, "❌ Введите корректное число")

@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout_query(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def process_successful_payment(message):
    chat_id = message.chat.id
    payment = message.successful_payment
    amount = payment.total_amount
    payment_id = payment.provider_payment_charge_id
    
    add_balance(chat_id, amount)
    add_transaction(chat_id, amount, 'refill', 'completed', payment_id)
    
    text = f"""✅ Платеж успешно обработан!

Вы пополнили баланс на <b>{amount} ⭐</b>

<i>ID платежа: {payment_id[:20]}...</i>

Спасибо за пополнение! Можете начать игру."""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎮 Играть", url="http://t.me/gift_pepe_bot/gift"))
    markup.add(types.InlineKeyboardButton("💰 Баланс", callback_data="balance"))
    markup.add(types.InlineKeyboardButton("⭐ Пополнить еще", callback_data="refill"))
    
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")

@bot.message_handler(commands=['stats'])
def stats(message):
    chat_id = message.chat.id
    stat = get_stats()
    
    text = f"""📊 Статистика Gift Cases

👥 Всего пользователей: <b>{stat['total_users']}</b>
💰 Общая выручка: <b>{stat['total_revenue']} ⭐</b>
⭐ Общий баланс: <b>{stat['total_balance']} ⭐</b>
✅ Завершено платежей: <b>{stat['completed_refills']}</b>"""
    
    bot.send_message(chat_id, text, parse_mode="HTML")

@bot.message_handler(commands=['top'])
def top_users(message):
    chat_id = message.chat.id
    users = get_top_users(10)
    
    if not users:
        bot.send_message(chat_id, "❌ Нет данных о пользователях")
        return
    
    text = "🏆 Топ 10 пользователей\n\n"
    for i, user in enumerate(users, 1):
        telegram_id, username, total_spent, balance = user
        text += f"{i}. <b>@{username or telegram_id}</b> - {total_spent} ⭐ потрачено\n"
    
    bot.send_message(chat_id, text, parse_mode="HTML")

@bot.message_handler(commands=['profile'])
def profile(message):
    chat_id = message.chat.id
    user = get_user_info(chat_id)
    transactions = get_user_transactions(chat_id, 5)
    
    if not user:
        bot.send_message(chat_id, "❌ Профиль не найден")
        return
    
    telegram_id, username, balance, total_spent, created_at, last_activity = user
    
    text = f"""👤 Ваш профиль

📱 Юзернейм: <b>@{username or 'N/A'}</b>
💰 Баланс: <b>{balance} ⭐</b>
💸 Всего потрачено: <b>{total_spent} ⭐</b>
📅 Аккаунт создан: <b>{created_at[:10]}</b>

📝 Последние транзакции:"""
    
    for trans in transactions:
        trans_id, amount, trans_type, status, trans_date = trans
        text += f"\n• {trans_type.upper()} {amount}⭐ ({status}) - {trans_date[:10]}"
    
    bot.send_message(chat_id, text, parse_mode="HTML")

@bot.message_handler(func=lambda message: True)
def handle_any_message(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="back"))
    
    bot.send_message(
        message.chat.id,
        "Используйте команду /start для начала работы",
        reply_markup=markup
    )

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    init_db()
    print("🎮 Gift Cases Bot запущен!")
    print(f"📊 БД: {DB_PATH}")
    print("📡 Ожидаем сообщений...")
    
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\n✋ Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
