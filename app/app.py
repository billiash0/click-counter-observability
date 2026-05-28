# -*- coding: utf-8 -*-

# 1. Импорт необходимых библиотек
import logging                     # Для записи логов (информация о кликах, ошибках и т.д.)
import os                          # Для чтения переменных окружения (Telegram токен, chat_id)
import requests                    # Для отправки HTTP-запросов (в Telegram и n8n)
from flask import Flask, render_template_string, request, Response
from prometheus_client import Counter, generate_latest, REGISTRY
from datetime import datetime

# 2. Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 3. Создание Flask-приложения
app = Flask(__name__)

# 4. Переменная для хранения количества кликов (в памяти)
click_count = 0

# 5. Prometheus-метрика: счётчик кликов
CLICKS = Counter('click_counter_total', 'Total number of clicks')

# 6. Чтение секретов из переменных окружения (файл .env)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')   # Токен Telegram-бота
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')       # ID чата (ваш личный ID)

# 7. Функция отправки сообщения в Telegram через бота
def send_telegram_message(text):
    """Отправляет сообщение в Telegram через Bot API."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials missing")   # Если нет токена или ID – предупреждение
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        # Отправляем POST-запрос с JSON-телом
        requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'HTML'}, timeout=5)
    except Exception as e:
        logger.error(f"Telegram error: {e}")

# 8. HTML-шаблон главной страницы (две кнопки)
HTML = '''
<!doctype html>
<html>
<body>
    <h1 id="counter">Clicks: {{ count }}</h1>
    <!-- Кнопка для увеличения счётчика кликов -->
    <button onclick="fetch('/click', {method: 'POST'}).then(r=>r.json()).then(d=>document.getElementById('counter').innerText='Clicks: '+d.clicks)">Click me!</button>
    <br><br>
    <!-- Кнопка "Who Am I" – отправляет данные о клиенте в n8n -->
    <button onclick="fetch('/whoami', {method: 'POST'}).then(() => alert('Data sent to bot!'))">Who Am I</button>
</body>
</html>
'''

# 9. Маршрут для главной страницы
@app.route('/')
def index():
    return render_template_string(HTML, count=click_count)

# 10. Маршрут для обработки кликов (увеличивает счётчик)
@app.route('/click', methods=['POST'])
def click():
    global click_count
    click_count += 1
    CLICKS.inc()                          # Увеличиваем Prometheus-метрику
    logger.info(f"Click detected! Total clicks: {click_count}")
    # Если количество кликов кратно 50 – отправляем Telegram-алерт
    if click_count % 50 == 0:
        send_telegram_message(f"🎉 <b>Достигнут {click_count}-й клик!</b>\nВсего кликов: {click_count}")
    return {'clicks': click_count}

# 11. Маршрут для Prometheus (метрики в формате text/plain)
@app.route('/metrics')
def metrics():
    return Response(generate_latest(REGISTRY), mimetype='text/plain')

# 12. Маршрут для кнопки "Who Am I"
@app.route('/whoami', methods=['POST'])
def whoami():
    """
    Собирает данные о клиенте (IP, User-Agent, язык, реферер и т.д.)
    и отправляет их в n8n вебхук. n8n, в свою очередь, пересылает их в Telegram.
    """
    # Формируем словарь с данными клиента
    client_data = {
        'ip': request.remote_addr,                         # IP-адрес клиента
        'user_agent': request.headers.get('User-Agent'),   # Браузер / устройство
        'accept_language': request.headers.get('Accept-Language'),  # Язык
        'referer': request.headers.get('Referer'),         # Откуда пришёл
        'x_forwarded_for': request.headers.get('X-Forwarded-For'),  # Реальный IP за прокси
        'timestamp': datetime.utcnow().isoformat()         # Время запроса (UTC)
    }
    # Логируем, что отправляем (для отладки)
    logger.info(f"Prepared client_data: {client_data}")

    # Адрес вебхука n8n. host.docker.internal – специальное имя хоста, которое из контейнера
    # обращается к хосту (вашему Mac). Порт 5678 – порт n8n.
    n8n_webhook_url = 'http://host.docker.internal:5678/webhook/whoami'

    try:
        response = requests.post(n8n_webhook_url, json=client_data, timeout=5)
        logger.info(f"WhoAmI data sent to n8n, status: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send WhoAmI data: {e}")

    # Возвращаем пустой ответ с кодом 204 (No Content)
    return '', 204

# 13. Точка входа – запуск приложения
if __name__ == '__main__':
    # host='0.0.0.0' – слушаем все интерфейсы внутри контейнера
    # port=5002 – порт, который проброшен в docker-compose.yml
    app.run(host='0.0.0.0', port=5002)