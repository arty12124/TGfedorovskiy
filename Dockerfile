# Используем официальный образ с Python 3.11
FROM python:3.11-slim

# Устанавливаем системные зависимости, нужные для сборки некоторых колёс
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libxml2-dev libxslt1-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем только файлы зависимостей сначала (для кэширования слоёв)
COPY requirements.txt /app/requirements.txt

# Обновляем pip и устанавливаем зависимости
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install -r /app/requirements.txt

# Копируем весь проект
COPY . /app

# Убедимся, что токен читается из переменных окружения (твой main.py должен использовать os.getenv("BOT_TOKEN")).
# Запуск
CMD ["python", "main.py"]
