FROM python:3.10-slim

# Устанавливаем необходимые зависимости для работы с локалью и библиотеками
RUN apt-get update && apt-get install -y locales && \
    sed -i '/ru_RU.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen ru_RU.UTF-8 && \
    echo "LANG=ru_RU.UTF-8" > /etc/default/locale

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV LANG=ru_RU.UTF-8 \
    LANGUAGE=ru_RU:ru \
    LC_ALL=ru_RU.UTF-8

EXPOSE 8123

CMD ["python", "bot.py"]
