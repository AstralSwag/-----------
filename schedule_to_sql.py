import pandas as pd
import sqlite3
import requests

def download_and_process_schedule(csv_url):

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

    # Загружаем CSV-файл
    file_path = './schedule.csv'
    df = pd.read_csv(file_path)

    # Обрезаем колонки после последней, которая не является пустой
    columns_to_keep = df.columns[:df.columns.get_loc("") + 1]
    df_filtered = df[columns_to_keep]

    # Находим последнюю дату и удаляем строки после неё
    date_rows = df_filtered['Дата'].dropna()
    last_date_index = date_rows.last_valid_index()
    df_filtered = df_filtered.loc[:last_date_index]

    # Переводим имена сотрудников и статусы
    name_mapping = {
        'Александр Д.': '@astralswag',
        'Софья': '@ssofpa',
        'Игорь': '@alwasready',
        'Дмитрий В.': '@mistah_grape',
        'Дмитрий С.': '@unknown_research',
        'Надежда': '@zloiorken',
        'Никита': '@Quwertyu',
        'Екатерина': '@ek_chizh',
        'Алексей': '@nofold888'
    }

    status_mapping = {
        'р': 'work',
        'о': 'vacation',
        '+': 'duty',
        'в': 'dayoff'
    }

    # Переименовываем столбцы на английский
    df_filtered.rename(columns={'Дата': 'Date', 'Unnamed: 0': 'Time'}, inplace=True)

    # Применяем преобразования
    for col in df_filtered.columns[2:]:  # Начинаем с третьей колонки, где начинаются имена сотрудников
        df_filtered[col] = df_filtered[col].map(lambda x: status_mapping.get(x, x))  # Заменяем статусы
        df_filtered[col] = df_filtered[col].replace(name_mapping)  # Заменяем имена

    # Создаём базу данных SQLite и записываем таблицу
    db_name = './schedule.db'
    table_name = 'schedule'

    conn = sqlite3.connect(db_name)
    df_filtered.to_sql(table_name, conn, if_exists='replace', index=False)
    conn.close()

    print("Данные успешно сохранены в базе данных.")
