# import pymodbus
# from pymodbus.client import ModbusTcpClient

# client = ModbusTcpClient(host='192.168.100.110', port=502)

# if client.connect():
#     result = client.read_input_registers(address=0, count=2)

#     if not result.isError():
#         print("Input Registers:")
#         for i, reg in enumerate(result.registers):
#             print(f"Address {i}: {reg}")
#     else:
#         print(f"Error reading input registers: {result}")
#     client.close()
# else:
#     print("Failed to connect to Modbus server.")


import time
from pymodbus.client import ModbusTcpClient

host = '192.168.100.110'
port = 502
polling_interval = 2  

client = ModbusTcpClient(host=host, port=port)
if client.connect():
    try:
        while True:
            result = client.read_input_registers(address=0, count=2)

            if not result.isError():
                print(f"Input Registers at {time.strftime('%H:%M:%S')}:")
                for i, reg in enumerate(result.registers):
                    print(f"Address {i}: {reg}")
            else:
                print(f"Error reading input registers at {time.strftime('%H:%M:%S')}: {result}")

            time.sleep(polling_interval)

    except KeyboardInterrupt:
        print("Stopped by user.")

    finally:
        client.close()
else:
    print("Failed to connect to Modbus server.")