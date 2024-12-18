import telebot
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
import os

# Загрузка переменных окружения
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TELEGRAM_BOT_TOKEN:
    print("TELEGRAM_BOT_TOKEN не найден в файле .env!")
    exit()

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Путь к базе данных SQLite
DB_PATH = './schedule.db'

# Функция для проверки, входит ли текущее время в заданный диапазон
def is_time_in_range(time_range, current_time):
    try:
        start_time, end_time = time_range.split('-')
        start_time = datetime.strptime(start_time.strip(), '%H:%M').time()
        end_time = datetime.strptime(end_time.strip(), '%H:%M').time()

        if start_time <= end_time:
            return start_time <= current_time <= end_time
        else:  # Случай, если смена ночная
            return current_time >= start_time or current_time <= end_time
    except ValueError:
        return False

# Обработка команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = telebot.types.KeyboardButton("Кто дежурит?")
    markup.add(button)
    bot.send_message(message.chat.id, "Привет. Просто нажми на охуенную кнопку ниже.", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Кто дежурит?")
def who_is_on_duty(message):
    try:
        # Подключение к базе данных SQLite
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Позволяет доступ к строкам как к словарям
        cursor = conn.cursor()

        # Получение текущей даты и времени
        now = datetime.now()
        current_date = now.strftime('%d.%m.%Y')
        current_time = now.time()

        # Лог текущей даты и времени для отладки
        print(f"Текущая дата: {current_date}, текущее время: {current_time}")

        # Запрос для получения дежурных на текущую дату
        query = """
        SELECT * FROM schedule
        WHERE Date = ?
        """
        cursor.execute(query, (current_date,))
        rows = cursor.fetchall()

        if not rows:
            bot.send_message(message.chat.id, "Сегодня никто не дежурит или данные недоступны.")
            print("На текущую дату данные отсутствуют.")
            return

        # Лог извлечённых строк для отладки
        print(f"Извлечённые строки: {rows}")

        # Поиск колонок со значением "duty" для текущего временного интервала
        on_duty = []
        for row in rows:
            time_range = row["Time"]
            if is_time_in_range(time_range, current_time):
                for col_name in row.keys():  # Доступ к именам колонок
                    value = row[col_name]  # Доступ к значениям колонок
                    if value == "duty":
                        on_duty.append(col_name)

        # Лог колонок дежурных для отладки
        print(f"Дежурные колонки: {on_duty}")

        if on_duty:
            bot.send_message(message.chat.id, f"Сейчас дежурят: {', '.join(on_duty)}")
        else:
            bot.send_message(message.chat.id, "Сейчас никто не дежурит.")

    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {e}")
        print(f"Ошибка: {e}")
    finally:
        conn.close()

# Запуск бота
print("Бот запущен...")
bot.infinity_polling()
