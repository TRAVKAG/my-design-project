FROM python:3.11-slim

WORKDIR /app

# Устанавливаем aiogram
RUN pip install --no-cache-dir aiogram

# Копируем файлы проекта
COPY . /app

# Команда запуска бота
CMD ["python", "bot.py"]
