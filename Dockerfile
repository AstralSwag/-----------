# Используем официальный образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY . /app

# Устанавливаем зависимости
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Открываем порт для взаимодействия
EXPOSE 5000

# Устанавливаем команду для запуска бота
CMD ["python", "bot.py"]
