import telebot
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import logging

# Загрузка переменных окружения
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TELEGRAM_BOT_TOKEN:
    print("TELEGRAM_BOT_TOKEN не найден в файле .env!")
    exit()

# Инициализация логирования
LOG_DIR = './logs'
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, f"{datetime.now().strftime('%d-%m-%Y')}.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Путь к базе данных SQLite
DB_PATH = './schedule.db'

# Глобальный словарь для хранения контекстов пользователей
user_context = {}

# Словарь статусов с переводами и эмодзи
STATUS_MAPPING = {
    'work': 'Рабочий день 👨🏻‍💻',
    'dayoff': 'Выходной 🌴',
    'vacation': 'Отпуск ✈️',
    'duty': 'Дежурный 🚨'
}

# Экранирование для MarkdownV2
SPECIAL_CHARS = r"_\*\[\]\(\)~`>#+\-=|{}\."

def escape_markdown(text):
    """Экранирование специальных символов для MarkdownV2"""
    import re
    return re.sub(f'([{SPECIAL_CHARS}])', r'\\\1', text)

def get_weekday(date_str):
    """Возвращает день недели для даты в формате DD.MM.YYYY"""
    weekdays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    date_obj = datetime.strptime(date_str, '%d.%m.%Y')
    return weekdays[date_obj.weekday()]

# Обработка команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_info = f"User: {message.from_user.first_name} (@{message.from_user.username or 'No username'})"
    logging.info(f"{user_info} sent /start")
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_duty = telebot.types.KeyboardButton("Кто дежурит?")
    button_schedule = telebot.types.KeyboardButton("Моё расписание")
    markup.add(button_duty, button_schedule)
    bot.send_message(message.chat.id, "Привет! Теперь я Матроскин_V2 и умею выводить твоё расписание!!!:", reply_markup=markup)




#Кто дежурит?
@bot.message_handler(func=lambda message: message.text == "Кто дежурит?")
def who_is_on_duty(message):
    user_info = f"User: {message.from_user.first_name} (@{message.from_user.username or 'No username'})"
    logging.info(f"{user_info} requested 'Кто дежурит?'")
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
            logging.info(f"{user_info} - No duty data available for today")
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
            logging.info(f"{user_info} - On duty: {', '.join(on_duty)}")
        else:
            bot.send_message(message.chat.id, "Сейчас никто не дежурит.")
            logging.info(f"{user_info} - No one is on duty now")

    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {e}")
        logging.error(f"{user_info} - Error: {e}")
        print(f"Ошибка: {e}")
    finally:
        conn.close()




#Моё расписание
@bot.message_handler(func=lambda message: message.text == "Моё расписание")
def my_schedule_handler(message):
    user_info = f"User: {message.from_user.first_name} (@{message.from_user.username or 'No username'})"
    logging.info(f"{user_info} requested 'Моё расписание'")
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("На завтра"),
        telebot.types.KeyboardButton("3️⃣"),
        telebot.types.KeyboardButton("7️⃣"),
        telebot.types.KeyboardButton("Покажи весь месяц")
    )
    bot.send_message(message.chat.id, "На сколько дней вперед вывести твоё расписание? 🗓", reply_markup=markup)
    user_context[message.chat.id] = {'command': 'my_schedule'}

@bot.message_handler(func=lambda message: message.chat.id in user_context and user_context[message.chat.id]['command'] == 'my_schedule')
def handle_schedule_days_input(message):
    user_info = f"User: {message.from_user.first_name} (@{message.from_user.username or 'No username'})"
    try:
        user_input = message.text.strip()
        if user_input == "На завтра":
            days = 2
        elif user_input == "3️⃣":
            days = 4
        elif user_input == "7️⃣":
            days = 8
        elif user_input == "Покажи весь месяц":
            days = 31  # Максимально возможное количество дней в месяце
        else:
            days = int(user_input)

        username = f"@{message.from_user.username}" if message.from_user.username else None

        if not username:
            bot.send_message(message.chat.id, "У вас нет никнейма в Telegram. Расписание не может быть найдено.")
            logging.info(f"{user_info} - No username provided, schedule lookup failed.")
            return

        # Подключение к базе данных
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем текущую дату
        today = datetime.now()
        last_day = today.replace(day=1) + timedelta(days=32)  # Переходим на следующий месяц
        last_day = last_day.replace(day=1) - timedelta(days=1)  # Последний день текущего месяца

        # Рассчитываем конечную дату вывода расписания
        end_date = today + timedelta(days=days - 1)
        if end_date > last_day:
            end_date = last_day
            bot.send_message(message.chat.id, "я пока умею работать только в пределах текущего месяца, сорри")

        # Форматируем даты для SQL
        start_date_str = today.strftime('%d.%m.%Y')
        end_date_str = end_date.strftime('%d.%m.%Y')

        # Запрос для получения расписания пользователя
        query = f"""
        SELECT Date, Time, `{username}`
        FROM schedule
        WHERE Date BETWEEN ? AND ?
        """
        cursor.execute(query, (start_date_str, end_date_str))
        rows = cursor.fetchall()

        if not rows:
            bot.send_message(message.chat.id, "Тебя нет в расписании, старина")
            logging.info(f"{user_info} - No schedule found for {username}")
        else:
            schedule = []
            for row in rows:
                status = row[username]
                if status is None:
                    continue
                formatted_status = STATUS_MAPPING.get(status, status)
                weekday = get_weekday(row['Date'])
                today_marker = " 👈 Сегодня" if row['Date'] == today.strftime('%d.%m.%Y') else ""
                if status == 'duty':
                    schedule.append(f"*{escape_markdown(row['Date'])}* \\({escape_markdown(weekday)}\\) \\- {escape_markdown(formatted_status)} {escape_markdown(row['Time'])}{escape_markdown(today_marker)}\n")
                else:
                    schedule.append(f"*{escape_markdown(row['Date'])}* \\({escape_markdown(weekday)}\\) \\- {escape_markdown(formatted_status)}{escape_markdown(today_marker)}\n")

            if schedule:
                table = "\n".join(schedule)
                bot.send_message(message.chat.id, table, parse_mode="MarkdownV2")
                logging.info(f"{user_info} - Schedule sent for {username}")
            else:
                bot.send_message(message.chat.id, "Тебя нет в расписании, старина")
                logging.info(f"{user_info} - No schedule found after filtering for {username}")

        # Возврат кнопок по умолчанию
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        button_duty = telebot.types.KeyboardButton("Кто дежурит?")
        button_schedule = telebot.types.KeyboardButton("Моё расписание")
        markup.add(button_duty, button_schedule)
        bot.send_message(message.chat.id, "____________", reply_markup=markup)

    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное число дней.")
        logging.info(f"{user_info} - Invalid input for schedule days.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {e}")
        logging.error(f"{user_info} - Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
        user_context.pop(message.chat.id, None)


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
    

# Запуск бота
logging.info("Бот запущен...")
bot.infinity_polling()
