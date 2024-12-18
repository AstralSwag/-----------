from dotenv import load_dotenv
import os
from schedule_to_sql import download_and_process_schedule

# Загружаем переменные окружения из файла .env
load_dotenv()

# Получаем ссылку на CSV файл из переменной окружения
csv_url = os.getenv('CSV_URL')

# Вызываем функцию, чтобы скачать и обработать CSV
download_and_process_schedule(csv_url)
