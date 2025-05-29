import telebot
import sqlite3
import requests

TELEGRAM_TOKEN = ''
OPENROUTER_API_KEY = ''

bot = telebot.TeleBot(TELEGRAM_TOKEN)
keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
button_1 = telebot.types.KeyboardButton('🔍Проверить информацию🔍')
keyboard.add(button_1)

def check_info(text):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "",
        "Content-Type": "application/json"
    }

    url = "https://openrouter.ai/api/v1/chat/completions"

    data = {
        "model": "deepseek/deepseek-chat-v3-0324:free",
        "messages": [
            {
                "role": "system",
                "content": "Ты — ассистент по проверке новостей. Пиши кратко и по-русски правда это или фейк. Не вставляй никаких ссылок."
            },
            {
                "role": "user",
                "content": f"Проверь, является ли эта новость фейком:\n\n{text}"
            }
        ]
    }

    con = sqlite3.connect('news.db')

    con.execute(f'''
            CREATE TABLE IF NOT EXISTS checked_news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                news TEXT,
                result TEXT
            )
        ''')

    previous_news = con.execute(f"SELECT result FROM checked_news WHERE news = '{text}'").fetchone()

    if previous_news is not None:
        con.close()
        return previous_news[0]
    else:
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code != 200:
                con.close()
                return f"❗️ Ошибка HTTP {response.status_code}: {response.text}"

            result = response.json()
            con.execute(f"INSERT INTO checked_news (news, result) VALUES ('{text}', '{result['choices'][0]['message']['content'].strip()}')")
            con.commit()
            con.close()
            return result['choices'][0]['message']['content'].strip()
        except Exception as e:
            con.close()
            return f"❗️ Ошибка при обращении к боту: {e}"

@bot.message_handler(commands=['start'])
def first_command(message):
    bot.send_message(message.chat.id,
        "👋Привет! Нажми на кнопку ниже, а после напиши текст своего вопроса, и я скажу, правдив он или нет.",
                     reply_markup=keyboard
    )

def delete_old_info():
    con = sqlite3.connect('news.db')
    all_news = con.execute('SELECT * FROM news').fetchall()
    if len(all_news) > 100:
        id = con.execute('SELECT id FROM news').fetchone()[0]
        con.execute(f"DELETE FROM news WHERE id BETWEEN {id} AND {id + 99}")
        con.commit()
    con.close()

@bot.message_handler(func = lambda message: message.text == '🔍Проверить информацию🔍')
def handle_check(message):
    bot.send_message(message.chat.id, "✋Напиши текст своего запроса.✍")
    bot.register_next_step_handler(message, open_check)

def open_check(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, "✋Напиши текст своего запроса более развёрнуто.✍")
        bot.register_next_step_handler(message, open_check)
        return
    bot.send_message(message.chat.id, "🔎Проверяю информацию...🔍")
    result = check_info(message.text)
    bot.send_message(message.chat.id, result)

bot.polling()
