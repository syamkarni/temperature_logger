from flask import Flask, render_template, request, redirect, send_file
import threading
import time
import sqlite3
from pymodbus.client import ModbusTcpClient
from fpdf import FPDF
import io

app = Flask(__name__)

# basic config
host = '192.168.100.110'
port = 502
polling_interval = 1
db_file = "logger_data.db"

latest_data = {
    "temperature": None,
    "humidity": None,
    "timestamp": None
}

def init_db():
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            temperature REAL,
            humidity REAL
        )
    ''')
    conn.commit()
    conn.close()

def insert_log(timestamp, temperature, humidity):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('''
        INSERT INTO logs (timestamp, temperature, humidity)
        VALUES (?, ?, ?)
    ''', (timestamp, temperature, humidity))
    conn.commit()
    conn.close()

def poll_modbus_data():
    global polling_interval
    client = ModbusTcpClient(host=host, port=port)
    if client.connect():
        try:
            while True:
                result = client.read_input_registers(address=0, count=2)
                if not result.isError():
                    temperature = result.registers[0] / 10.0
                    humidity = result.registers[1] / 10.0
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

                    latest_data.update({
                        "temperature": temperature,
                        "humidity": humidity,
                        "timestamp": timestamp
                    })

                    insert_log(timestamp, temperature, humidity)
                    print(f"Logged at {timestamp}")
                else:
                    print(f"Error reading registers")

                time.sleep(polling_interval)
        except Exception as e:
            print(f"Polling Error: {e}")
        finally:
            client.close()
    else:
        print("Failed to connect to Modbus server.")

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html', data=latest_data, interval=polling_interval)

@app.route('/set_interval', methods=['POST'])
def set_interval():
    global polling_interval
    new_interval = request.form.get('interval')
    try:
        polling_interval = int(new_interval)
    except:
        pass
    return redirect('/')

@app.route('/export', methods=['GET', 'POST'])
def export():
    if request.method == 'POST':
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')

        start_time = start_time.replace('T', ' ') + ":00"
        end_time = end_time.replace('T', ' ') + ":00"

        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        c.execute('''
            SELECT timestamp, temperature, humidity
            FROM logs
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC
        ''', (start_time, end_time))

        rows = c.fetchall()
        conn.close()

        if not rows:
            return "No data found for given time range."

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, "Temperature and Humidity Log", ln=True, align="C")
        pdf.cell(0, 10, f"From {start_time} to {end_time}", ln=True, align="C")
        pdf.ln(10)

        pdf.cell(60, 10, "Timestamp", 1)
        pdf.cell(40, 10, "Temperature (°C)", 1)
        pdf.cell(40, 10, "Humidity (%)", 1)
        pdf.ln()

        for timestamp, temperature, humidity in rows:
            pdf.cell(60, 10, timestamp, 1)
            pdf.cell(40, 10, f"{temperature}", 1)
            pdf.cell(40, 10, f"{humidity}", 1)
            pdf.ln()

        pdf_bytes = pdf.output(dest='S').encode('latin1')
        pdf_stream = io.BytesIO(pdf_bytes)

        return send_file(pdf_stream, download_name="log_data.pdf", as_attachment=True)

    return render_template('export.html')

if __name__ == '__main__':
    init_db()

    polling_thread = threading.Thread(target=poll_modbus_data)
    polling_thread.daemon = True
    polling_thread.start()
    app.run(host='0.0.0.0', port=5050)
