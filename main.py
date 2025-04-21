from flask import Flask, render_template, request, redirect, send_file
import threading
import time
from pymodbus.client import ModbusTcpClient
from fpdf import FPDF
import io

app = Flask(__name__)

# basic config
host = '192.168.100.110'
port = 502
polling_interval = 5 
log_data = []  

latest_data = {
    "temperature": None,
    "humidity": None,
    "timestamp": None
}

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

                    log_data.append({
                        "timestamp": timestamp,
                        "temperature": temperature,
                        "humidity": humidity
                    })
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

        filtered = [
            entry for entry in log_data
            if start_time <= entry['timestamp'] <= end_time
        ]

        if not filtered:
            return "No data in this range."

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

        for row in filtered:
            pdf.cell(60, 10, row['timestamp'], 1)
            pdf.cell(40, 10, str(row['temperature']), 1)
            pdf.cell(40, 10, str(row['humidity']), 1)
            pdf.ln()

        pdf_bytes = pdf.output(dest='S').encode('latin1')
        pdf_stream = io.BytesIO(pdf_bytes)

        return send_file(pdf_stream, download_name="log_data.pdf", as_attachment=True)

    return render_template('export.html')

if __name__ == '__main__':
    polling_thread = threading.Thread(target=poll_modbus_data)
    polling_thread.daemon = True
    polling_thread.start()
    app.run(host='0.0.0.0', port=5050)
