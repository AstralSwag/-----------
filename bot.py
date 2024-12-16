import csv
import json
import requests
from collections import defaultdict
from dotenv import load_dotenv
import os

# Загружаем переменные окружения из файла .env
load_dotenv()

# Получаем ссылку на CSV файл из переменной окружения
csv_url = os.getenv('CSV_FILE_PATH')

# Проверяем, что ссылка существует
if not csv_url:
    print("URL не найден в .env файле!")
    exit()

# Скачиваем CSV файл
response = requests.get(csv_url)

# Проверяем успешность запроса
if response.status_code == 200:
    # Сохраняем файл
    with open('schedule.csv', 'wb') as f:
        f.write(response.content)
    print("CSV файл успешно скачан и сохранен как 'schedule.csv'.")
else:
    print(f"Ошибка при скачивании файла: {response.status_code}")
    exit()

# Открываем скачанный CSV файл
with open('schedule.csv', 'r', encoding='utf-8') as file:
    reader = csv.reader(file)
    header = next(reader)  # Прочитаем заголовки

    # Создаем структуру данных для хранения информации
    data = defaultdict(list)

    # Перебираем строки с данными
    current_date = None
    for row in reader:
        # Пропускаем пустые строки или строки с метками типа "Выходной", "Рабочий", "Дежурство" и т.д.
        if not row[0] or row[0].startswith(('Выходной', 'Рабочий', 'Дежурство', 'Отпуск')):
            continue

        date = row[0].strip()  # Дата
        time_intervals = row[1:]  # Интервалы и статусы

        # Если дата изменилась, фиксируем её
        if date != current_date:
            current_date = date

        # Обрабатываем интервалы и статусы для сотрудников
        for i, status in enumerate(time_intervals[1:], start=1):  # Начинаем с индекса 1, так как первый элемент — это интервал
            if status:  # Если статус есть, добавляем информацию
                employee_name = header[i]
                if status == '+':  # Дежурный
                    data[date].append({"Сотрудник": employee_name, "интервал": time_intervals[0], "статус": "дежурный"})
                elif status == 'р':  # Работает
                    data[date].append({"Сотрудник": employee_name, "интервал": "весь день", "статус": "работает"})
                elif status == 'о':  # В отпуске
                    data[date].append({"Сотрудник": employee_name, "интервал": "весь день", "статус": "в отпуске"})
                elif status == 'в':  # Выходной
                    data[date].append({"Сотрудник": employee_name, "интервал": "весь день", "статус": "выходной"})

    # Запись данных в JSON
    with open('schedule.json', 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

    print("Данные успешно сохранены в 'schedule.json'.")
