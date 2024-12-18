import telebot
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TELEGRAM_BOT_TOKEN:
    print("TELEGRAM_BOT_TOKEN not found in .env file!")
    exit()

# Initialize the bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Path to the SQLite database
DB_PATH = './schedule.db'

# Function to check if current time is in the given range
def is_time_in_range(time_range, current_time):
    try:
        start_time, end_time = time_range.split('-')
        start_time = datetime.strptime(start_time.strip(), '%H:%M').time()
        end_time = datetime.strptime(end_time.strip(), '%H:%M').time()

        if start_time <= end_time:
            return start_time <= current_time <= end_time
        else:  # Overnight shift case
            return current_time >= start_time or current_time <= end_time
    except ValueError:
        return False

# Command to handle the "Who is on duty?" button
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = telebot.types.KeyboardButton("Who is on duty?")
    markup.add(button)
    bot.send_message(message.chat.id, "Hi! I can help you find out who's on duty today. Just press the button below!", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Who is on duty?")
def who_is_on_duty(message):
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Allows access to rows as dictionaries
        cursor = conn.cursor()

        # Get the current date and time
        now = datetime.now()
        current_date = now.strftime('%d.%m.%Y')
        current_time = now.time()

        # Log current date and time for debugging
        print(f"Current date: {current_date}, Current time: {current_time}")

        # Query to find the duty employee for the current date
        query = """
        SELECT * FROM schedule
        WHERE Date = ?
        """
        cursor.execute(query, (current_date,))
        rows = cursor.fetchall()

        if not rows:
            bot.send_message(message.chat.id, "No one is on duty or data is unavailable today.")
            print("No rows found for the current date.")
            return

        # Log rows for debugging
        print(f"Rows retrieved: {rows}")

        # Find the columns with "duty" for the current time interval
        on_duty = []
        for row in rows:
            time_range = row["Time"]
            if is_time_in_range(time_range, current_time):
                for col_name in row.keys():  # Access column names
                    value = row[col_name]  # Access column values
                    if value == "duty":
                        on_duty.append(col_name)

        # Log duty columns for debugging
        print(f"On duty columns: {on_duty}")

        if on_duty:
            bot.send_message(message.chat.id, f"Currently on duty: {', '.join(on_duty)}")
        else:
            bot.send_message(message.chat.id, "No one is on duty right now.")

    except Exception as e:
        bot.send_message(message.chat.id, f"An error occurred: {e}")
        print(f"Error occurred: {e}")
    finally:
        conn.close()

# Run the bot
print("Bot is running...")
bot.infinity_polling()
