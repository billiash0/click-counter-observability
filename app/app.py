import logging
from flask import Flask, render_template_string, request, Response
from prometheus_client import Counter, generate_latest, REGISTRY

# Настраиваем логирование – эти логи автоматически отправятся в SigNoz
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Состояние счётчика
click_count = 0

# Prometheus метрика
CLICKS = Counter('click_counter_total', 'Total number of clicks')

# HTML‑страница с кнопкой (используем простой шаблон)
HTML = '''
<!doctype html>
<html lang="ru">
<head><title>Click Counter</title></head>
<body>
    <h1 id="counter">Clicks: {{ count }}</h1>
    <button onclick="fetch('/click', {method: 'POST'}).then(r=>r.json()).then(d=>document.getElementById('counter').innerText='Clicks: '+d.clicks)">
        Click me!
    </button>
</body>
</html>
'''

@app.route('/')
def index():
    """Главная страница – счётчик и кнопка"""
    return render_template_string(HTML, count=click_count)

@app.route('/click', methods=['POST'])
def click():
    """Обработчик клика – увеличивает счётчик и логирует событие"""
    global click_count
    click_count += 1
    CLICKS.inc()
    # Этот лог будет отправлен в SigNoz
    logger.info(f"Click detected! Total clicks: {click_count}")
    return {'clicks': click_count}

@app.route('/metrics')
def metrics():
    """Эндпоинт для Prometheus – отдаёт метрики в формате text/plain"""
    return Response(generate_latest(REGISTRY), mimetype='text/plain')

if __name__ == '__main__':
    # Приложение слушает на всех интерфейсах внутри контейнера, порт 5002
    app.run(host='0.0.0.0', port=5002)