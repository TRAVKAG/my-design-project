FROM python:3.11-slim

WORKDIR /app

# Устанавливаем библиотеки для бота и веб-сервера
RUN pip install --no-cache-dir aiogram aiohttp

# Копируем все файлы проекта в контейнер
COPY . /app

# Запускаем бота
CMD ["python", "bot.py"]
