import csv
import json
import requests
from collections import defaultdict


def download_and_process_schedule(csv_url, output_json_path):
    """
    Загружает CSV файл с расписанием по URL и сохраняет обработанное расписание в JSON.

    :param csv_url: Строка с URL на CSV файл
    :param output_json_path: Путь к JSON файлу, куда сохранить результат
    """
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

    # Считываем CSV файл
    schedule = defaultdict(list)  # schedule[день] = [список сотрудников с их статусами]
    
    current_date = None

    # Открываем CSV и обрабатываем его
    with open('schedule.csv', 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        header = next(reader)  # Чтение первой строки - заголовков (имена сотрудников)
        
        # Чтение строк с данными
        for row in reader:
            # Если первая ячейка не пустая, то это новая дата
            if row[0]:
                current_date = get_date(row[0].strip())  # Дата

            # Второй столбец - это интервал времени
            interval = row[1].strip()

            # Считываем статусы сотрудников для текущего интервала
            for i, status in enumerate(row[2:], start=2):
                employee_name = header[i]

                if employee_name == "":
                    break

                status_for_employee = ""
                
                # Если статус "р" или "в" — ставим статус на весь день
                if status == 'р':
                    status_for_employee = "работает"
                elif status == 'в':
                    status_for_employee = "выходной"
                elif status == 'о':
                    status_for_employee = "в отпуске"
                elif status == '+':
                    status_for_employee = f"дежурит {interval}"
                
                if status_for_employee != "":
                    schedule[current_date].append({employee_name: {"статус": status_for_employee}})

    # Запись данных в JSON
    with open(output_json_path, 'w', encoding='utf-8') as json_file:
        json.dump(schedule, json_file, ensure_ascii=False, indent=4)

    print(f"Данные успешно сохранены в '{output_json_path}'.")

def get_date(rus_date):

    parts = rus_date.split(', ')
    day = parts[1].split(' ')[0]
    month_cyr = parts[1].split(' ')[1]

    month_mapping = {
        'янв': '01',
        'фев': '02',
        'мар': '03',
        'апр': '04',
        'май': '05',
        'июн': '06',
        'июл': '07',
        'авг': '08',
        'сен': '09',
        'окт': '10',
        'ноя': '11',
        'дек': '12'
    }
    month = month_mapping.get(month_cyr, '01')

    year = '2024'
    return f"{year}-{month}-{day.zfill(2)}"