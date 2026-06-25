from pymodbus.client import ModbusSerialClient as ModbusClient
import time

# Initialize the Modbus serial client
client = ModbusClient(
    port='/dev/ttyUSB0',
    baudrate=9600,
    timeout=5,  # Increased timeout
    parity='N',
    stopbits=1,
    bytesize=8
)

def modbusConnect(address, value, slaveID):
    if client.connect():
        print("Connected to Modbus server.")
        try:
            # Write to coil
            write_response = client.write_coil(address, bool(value), slave=slaveID)
            if write_response.isError():
                print(f"Error writing to coil: {write_response}")
            else:
                print(f"Set coil at address {address} to {'ON' if value else 'OFF'}")

            time.sleep(1)

            # Read coil
            read_response = client.read_coils(address, 1, slave=slaveID)
            if read_response.isError():
                print(f"Error reading from coil: {read_response}")
            else:
                print(f"Coil status at address {address}: {'ON' if read_response.bits[0] else 'OFF'}")
        finally:
            client.close()
    else:
        print("Failed to connect to Modbus server.")

try:
    while True:
        # Get user input for address and value
        slaveID = input("Input your Slave Id (decimal): ").strip()
        address = input("Input your address (decimal): ").strip()
        value = input("Input your value (0 for OFF, 1 for ON): ").strip()
        
        try:
            # Convert inputs to integers
            slaveID = int(slaveID)
            address = int(address)  # Address should be an integer
            value = int(value)      # Value should be 0 or 1
            
            # Check if value is valid for coil (0 or 1)
            if value not in [0, 1]:
                print("Invalid value. Enter 0 for OFF or 1 for ON.")
                continue
        except ValueError:
            print("Invalid input. Please enter numbers only.")
            continue
        
        # Call the modbusConnect function with the user-provided address and value
        modbusConnect(address=address, value=value, slaveID=slaveID)
except KeyboardInterrupt:
    print("\nExiting...")
finally:
    client.close()  # Close the serial port if open
