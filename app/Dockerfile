# Используем официальный лёгкий образ Python
FROM python:3.11-slim

# Рабочая директория внутри контейнера
WORKDIR /app

# Копируем файл с зависимостями и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код приложения
COPY app.py .

# Настройки OpenTelemetry (автоматический сбор логов и метрик)
ENV OTEL_SERVICE_NAME=click-counter-app   
# Имя сервиса в SigNoz
ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:4317   
# Адрес OTLP коллектора (gRPC)
ENV OTEL_EXPORTER_OTLP_LOGS_PROTOCOL=grpc 
# Используем gRPC для логов
ENV OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true   
# Автоматический перехват логов

# Запуск приложения с автоинструментацией OpenTelemetry
CMD ["opentelemetry-instrument", "python", "app.py"]