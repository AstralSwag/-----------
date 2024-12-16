import csv
import logging
import pandas as pd
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime, time
from dotenv import load_dotenv
import requests
import tempfile



TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CSV_FILE_PATH = os.getenv('CSV_FILE_PATH', 'schedule.csv')


# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

EMPLOYEES = ["Александр Д.", "Софья", "Игорь", "Дмитрий В.", "Дмитрий С.", "Надежда", "Никита", "Екатерина", "Алексей"]


def download_csv(url):
    """Скачивает CSV файл по URL и сохраняет его в временный файл."""
    response = requests.get(url)
    if response.status_code == 200:

        

        temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w', newline='', encoding='utf-8')

        temp_file.write(response.content.decode('utf-8'))
        temp_file.close()
        return temp_file.name
    else:
        logger.error(f"Не удалось скачать CSV файл: {response.status_code}")
        return None
if CSV_FILE_PATH.startswith('http'):
    CSV_FILE_PATH = download_csv(CSV_FILE_PATH)

    # Создадим словарь для замены русских месяцев на английские
month_translation = {
    'янв': 'Jan', 'фев': 'Feb', 'мар': 'Mar', 'апр': 'Apr', 'май': 'May', 'июн': 'Jun',
    'июл': 'Jul', 'авг': 'Aug', 'сен': 'Sep', 'окт': 'Oct', 'ноя': 'Nov', 'дек': 'Dec'
}

def parse_russian_date(date_str):
    """
    Парсит строку с русским месяцем в формате 'день месяц' (например '1 дек')
    и возвращает объект datetime.
    """
    # Убираем день недели (если есть) и убираем точку из месяца
    date_str = date_str.split(',')[1].strip().replace('.', '')
    
    # Заменяем русский месяц на английский
    for ru_month, en_month in month_translation.items():
        if ru_month in date_str:
            date_str = date_str.replace(ru_month, en_month)
            break

    try:
        # Теперь парсим с английским месяцем
        date_obj = datetime.strptime(date_str, '%d %b')
        # Подставляем текущий год
        date_obj = date_obj.replace(year=datetime.now().year)
        return date_obj
    except Exception as e:
        print(f"Ошибка при разборе даты: {date_str} - {e}")
        return None

def parse_csv(csv_path):
    schedule = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # пропускаем заголовок

        current_date = None
        day_records = []  # временное хранилище строк для текущего дня

        for row in reader:
            first_col = row[0].strip()
            interval_col = row[1].strip() if len(row) > 1 else ""

            # Проверка: начало нового дня.
            if first_col:
                # Если уже были накоплены данные по предыдущему дню, обрабатываем их
                if current_date and day_records:
                    process_day_records(schedule, current_date, day_records)
                    day_records.clear()

                try:
                    # Парсим дату с использованием новой функции
                    date_obj = parse_russian_date(first_col)
                    if date_obj:
                        current_date = date_obj.date()
                    else:
                        current_date = None
                except Exception as e:
                    logger.error(f"Ошибка при разборе даты: {first_col} - {e}")
                    current_date = None

            # Накопим строки для текущего дня
            if current_date:
                day_records.append(row)

        # Не забудем обработать последний день в файле
        if current_date and day_records:
            process_day_records(schedule, current_date, day_records)

    return schedule



def process_day_records(schedule, current_date, day_records):
    """
    Обрабатывает накопленные строки за один день и записывает результат в schedule.
    day_records - это список строк (list of list), первый элемент из них содержит дату и первый интервал.
    Пример структуры day_records для буднего дня (3 интервала):
    [
      [ "пн, 2 дек.", "7:30-14:30", "", "+", ...],
      [ "", "10:00-19:00", "р", "", "в", ...],
      [ "", "14:30-22:30", "", "+", ..., ]
    ]

    Для выходного дня (2 интервала) будет только 2 строки соответственно.

    Логика:
    - Сначала определяем, сколько интервалов: это длина day_records.
    - Для каждого интервала парсим время.
    - Определяем дневные статусы сотрудников (о, в, р) и дежурства (+).
    """
    schedule[current_date] = {'intervals': []}

    # Соберём информацию по всем интервалам
    # day_states[employee] = 'о', 'в', 'р' или None
    # Если для дня у сотрудника встречается 'о' или 'в', то этот сотрудник весь день не дежурит.
    # Если встречается 'р', но нет 'о' или 'в', сотрудник работает.
    # '+' - дежурство в конкретном интервале, если нет 'о' или 'в'.
    day_states = {e: None for e in EMPLOYEES}

    # Сначала пройдём по всем интервалам и соберём дневые статусы (о, в, р).
    for row in day_records:
        # Интервал во 2-й колонке
        interval_str = row[1].strip() if len(row) > 1 else ""

        # Пройдёмся по сотрудникам
        for i, emp in enumerate(EMPLOYEES, start=2):
            if i < len(row):
                symbol = row[i].strip()
                if symbol in ['о', 'в']:
                    # Отпуск или выходной - сбрасываем день для этого сотрудника
                    day_states[emp] = symbol
                elif symbol == 'р':
                    # Рабочий день (если ещё не было 'о' или 'в')
                    # Установим 'р' только если нет 'о' или 'в'
                    if day_states[emp] not in ['о', 'в']:
                        day_states[emp] = 'р'

    # Теперь сформируем данные по интервалам.
    for row in day_records:
        interval_str = row[1].strip() if len(row) > 1 else ""
        if not interval_str:
            continue

        # Парсим время интервала
        start_time, end_time = parse_interval_time(interval_str)

        # Определяем дежурства на этот интервал
        duties = {}
        for i, emp in enumerate(EMPLOYEES, start=2):
            symbol = row[i].strip() if i < len(row) else ""
            # Если у сотрудника день 'о' или 'в', он не может дежурить
            if day_states[emp] in ['о', 'в']:
                duties[emp] = False
            else:
                # Если день 'р' или None, смотрим на символ интервала
                if symbol == '+':
                    duties[emp] = True
                else:
                    duties[emp] = False

        interval_info = {
            'start_time': start_time,
            'end_time': end_time,
            'duties': duties,
            'day_states': day_states.copy()
        }
        schedule[current_date]['intervals'].append(interval_info)


def parse_interval_time(interval_str):
    """
    Парсит строку вида "7:30-14:30" и возвращает (start_time, end_time) в формате time.
    """
    try:
        start_str, end_str = interval_str.split('-')
        start = datetime.strptime(start_str.strip(), '%H:%M').time()
        end = datetime.strptime(end_str.strip(), '%H:%M').time()
        return start, end
    except Exception as e:
        logger.error(f"Ошибка при разборе интервала времени '{interval_str}': {e}")
        return None, None


def get_current_duty(schedule):
    """
    Определяет, кто дежурит в данный момент.
    Перебирает даты и интервалы, находит текущий день и проверяет интервалы.
    Для упрощения считаем, что расписание на текущий день уже есть.
    """
    now = datetime.now()
    today = now.date()
    current_time = now.time()

    if today not in schedule:
        return None

    for interval in schedule[today]['intervals']:
        if interval['start_time'] and interval['end_time']:
            if interval['start_time'] <= current_time <= interval['end_time']:
                # Найдём всех, кто дежурит
                on_duty = [emp for emp, d in interval['duties'].items() if d]
                if on_duty:
                    return on_duty
    return None


# if __name__ == '__main__':
#     schedule_data = parse_csv(CSV_FILE_PATH)
#     # Пример использования:
#     # Определим, кто дежурит сейчас
#     now_duty = get_current_duty(schedule_data)
#     if now_duty:
#         print("Сейчас дежурят:", ", ".join(now_duty))
#     else:
#         print("Сейчас нет дежурных или расписание не найдено.")


#БОТ



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Кто сейчас дежурит?", callback_data='current_duty')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выберите действие:', reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    schedule_data = parse_csv(CSV_FILE_PATH)

    if query.data == 'current_duty':
        if schedule_data:
            duty_person = get_current_duty(schedule_data)
            if duty_person:
                response_text = f"Сейчас дежурит: {duty_person}"
            else:
                response_text = "Сейчас нет дежурных."
        else:
            response_text = "Не удалось получить данные о дежурных."

        await query.edit_message_text(text=response_text)

def main():
    # Создание экземпляра приложения
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button))

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()