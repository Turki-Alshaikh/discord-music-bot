from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "🟢 البوت يعمل بكفاءة 24/7 بدون توقف!"

def run():
    # فتح البورت 8080 عشان يتعرف عليه Render
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()