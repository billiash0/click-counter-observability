import logging
import os
import requests
from flask import Flask, render_template_string, request, Response
from prometheus_client import Counter, generate_latest, REGISTRY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
click_count = 0
CLICKS = Counter('click_counter_total', 'Total number of clicks')

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials missing")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'HTML'}, timeout=5)
    except Exception as e:
        logger.error(f"Telegram error: {e}")

HTML = '''
<!doctype html>
<html><body>
    <h1 id="counter">Clicks: {{ count }}</h1>
    <button onclick="fetch('/click', {method: 'POST'}).then(r=>r.json()).then(d=>document.getElementById('counter').innerText='Clicks: '+d.clicks)">Click me!</button>
</body></html>
'''

@app.route('/')
def index():
    return render_template_string(HTML, count=click_count)

@app.route('/click', methods=['POST'])
def click():
    global click_count
    click_count += 1
    CLICKS.inc()
    logger.info(f"Click detected! Total clicks: {click_count}")
    if click_count % 50 == 0:
        send_telegram_message(f"🎉 <b>Достигнут {click_count}-й клик!</b>\nВсего кликов: {click_count}")
    return {'clicks': click_count}

@app.route('/metrics')
def metrics():
    return Response(generate_latest(REGISTRY), mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
