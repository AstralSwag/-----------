from dotenv import load_dotenv
import os
from schedule_processor import download_and_process_schedule

# Загружаем переменные окружения из файла .env
load_dotenv()

# Получаем ссылку на CSV файл из переменной окружения
csv_url = os.getenv('CSV_URL')

# Путь к JSON файлу, куда будет сохранено расписание
output_json_path = 'schedule.json'

# Вызываем функцию, чтобы скачать и обработать CSV
download_and_process_schedule(csv_url, output_json_path)
