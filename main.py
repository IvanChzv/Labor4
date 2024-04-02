import subprocess
from flask import Flask, render_template, jsonify, request
import sqlite3
import psutil
import datetime
import smtplib
from email.mime.text import MIMEText
app = Flask(__name__)
# Критические значения по умолчанию
temperature_critical = 80
cpu_critical = 90
memory_critical = 90
@app.route("/")
def home():
    return render_template('index.html', temperature_critical=temperature_critical, cpu_critical=cpu_critical, memory_critical=memory_critical)

@app.route('/save_thresholds', methods=['POST'])
def save_thresholds():
    global temperature_critical, cpu_critical, memory_critical
    temperature_critical = int(request.form['temperature_critical'])
    cpu_critical = int(request.form['cpu_critical'])
    memory_critical = int(request.form['memory_critical'])
    return render_template('index.html', temperature_critical=temperature_critical, cpu_critical=cpu_critical, memory_critical=memory_critical)


@app.route("/data")
def get_data():

    conn = sqlite3.connect("server_data.db")
    cursor = conn.cursor()
    
    # Получение параметра interval из запроса
    interval = request.args.get('interval', '1m')
    
    # Определение временного интервала, основываясь на выбранном значении
    current_time = datetime.datetime.now()
    if interval == '1m':
        start_time = current_time - datetime.timedelta(minutes=1)
    elif interval == '1h':
        start_time = current_time - datetime.timedelta(hours=1)
    elif interval == '1d':
        start_time = current_time - datetime.timedelta(days=1)
    elif interval == '1w':
        start_time = current_time - datetime.timedelta(weeks=1)
    else:
        start_time = current_time - datetime.timedelta(minutes=1)
    
    cursor.execute("SELECT * FROM server_data WHERE timestamp >= ? ORDER BY timestamp ASC", (start_time,))
    data = cursor.fetchall()
    conn.close()
    
    formatted_data = []
    for entry in data:
        timestamp = entry[0]
        cpu_temperature = float(entry[1])
        cpu_load = float(entry[2])
        memory_usage = float(entry[3])
        formatted_data.append((timestamp, cpu_temperature, cpu_load, memory_usage))

    

    return jsonify({'data': formatted_data})
def get_cpu_temperature():
    output = subprocess.check_output(['sensors'])
    temperature = 0
    lines = output.decode().split('\n')
    for line in lines:
        if 'Tctl:' in line:
            temperature_str = line.split(':')[1].split()[0]
            temperature = float(temperature_str[:-2])
            break
    return temperature
def get_memory_usage():
    memory = psutil.virtual_memory().percent
    return memory
def get_server_stats():
    cpu_load = psutil.cpu_percent()
    cpu_temperature = get_cpu_temperature()
    memory_usage = get_memory_usage()
    return cpu_load, cpu_temperature, memory_usage
def save_server_stats():
    cpu_load, cpu_temperature, memory_usage = get_server_stats()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect("server_data.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO server_data VALUES (?, ?, ?, ?)", (timestamp, cpu_temperature, cpu_load, memory_usage))
    conn.commit()
    conn.close()
def send_email(subject, message):
    print("Отправлно письмо на почту")
    # Замените значения настройками вашей электронной почты
    sender_email = "vanya.chazov@internet.ru"
    sender_password = "Tjy5mH9sJDmgg2npf16U"
    receiver_email = "chazov.vanya2018@yandex.ru"
    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email
    with smtplib.SMTP("smtp.mail.ru", 587) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())

def check_thresholds(cpu_critical, temperature_critical, memory_critical):
    cpu_load, cpu_temperature, memory_usage = get_server_stats()
    # Здесь можно задать критические значения и отправлять уведомления при их превышении
    if cpu_load > cpu_critical:
        send_email("CPU Load Alert", f"CPU load is high: {cpu_load}%")
    if cpu_temperature > temperature_critical:
        send_email("CPU Temperature Alert", f"CPU temperature is high: {cpu_temperature}°C")
    if memory_usage > memory_critical:
        send_email("Memory Usage Alert", f"Memory usage is high: {memory_usage}%")

@app.before_request
def setup():
    global temperature_critical, cpu_critical, memory_critical
    conn = sqlite3.connect("server_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS server_data (
            timestamp TEXT,
            cpu_temperature REAL,
            cpu_load REAL,
            memory_usage REAL
        )
    """)
    conn.commit()
    conn.close()
    save_server_stats()  # Сохранение данных перед каждым запросом
    # Получение актуальных значений из формы
    check_thresholds(cpu_critical, temperature_critical, memory_critical)

if __name__ == "__main__":
    print("Запускаем")
    app.run(host='0.0.0.0', port=8080)
    
