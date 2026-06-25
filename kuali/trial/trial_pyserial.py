import serial
import time
import binascii

# Configure the serial port
ser = serial.Serial(
    port='/dev/ttyUSB0',       # Replace with your port
    baudrate=9600,
    timeout=1
)

# Function to calculate CRC-16 (Modbus)
def calculate_crc(data):
    # Compute CRC using the Modbus polynomial
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if (crc & 0x0001):
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, 'little')  # Return CRC as a 2-byte sequence (little-endian)

# Function to send hex data with CRC
def send_hex_with_crc(data):
    data_bytes = bytes.fromhex(data)  # Convert hex string to bytes
    crc = calculate_crc(data_bytes)   # Calculate CRC
    data_with_crc = data_bytes + crc  # Append CRC to the data
    ser.write(data_with_crc)          # Send the data with CRC
    print(f"Sent: {data} + CRC: {crc.hex()}")
    
# Function to send hex data
def send_hex(data):
    ser.write(bytes.fromhex(data))  # Convert hex string to bytes and send
    print(f"Sent: {data}")

# Function to Control Relay
def RelayControl(address, relay, status):
    # Convert address, relay, and status to hex strings with specified formatting
    # Pad each to be two characters if necessary
    address_str = f"{int(address, 16):02X}"
    relay_str = f"{int(relay, 16):02X}"
    status_str = f"{int(status, 16):02X}"
    
    # Construct the final string with fixed values 0500 and 00 as specified
    result = f"{address_str}0500{relay_str}{status_str}00"
    
    return result

# Function to read hex data
def read_hex(timeout=1):
    start_time = time.time()
    while True:
        if ser.in_waiting > 0:  # Check if there is data waiting to be read
            data = ser.read(ser.in_waiting)  # Read all available data
            print("Received:", data.hex())   # Print as hex string         
            return data.hex()
        
        # Check if we've reached the timeout
        if (time.time() - start_time) > timeout:
            print("Timeout: No response received.")
            return None
        
        # Short delay to avoid busy-waiting
        time.sleep(0.1)

try:
    # Loop to continuously prompt for user input, send data, and receive feedback
    while True:
        # Get hex input from the user
        selection = input("Select 00 to parameter or 01 to control: ").strip()
        if selection == "00":
            user_input = input("Send your hex Code: ").strip()

            # Validate the input
            try:
                bytes.fromhex(user_input)  # Check if input is valid hex
            except ValueError:
                print("Invalid hex input. Please try again.")
                continue
            # Send the inputted hex data with CRC
            send_hex_with_crc(user_input)
            # Clear the buffer after reading
            ser.reset_input_buffer()
        elif selection == "01":
            address = input("Input your address: ").strip()
            relay = input("Input your relay: ").strip()
            status = input("Input your status: ").strip()

            # Validate the input
            try:
                bytes.fromhex(address)  # Check if input is valid hex
                bytes.fromhex(relay)  # Check if input is valid hex
                bytes.fromhex(status)  # Check if input is valid hex
            except ValueError:
                print("Invalid hex input. Please try again.")
                continue
            # Send the inputted hex data with CRC
            send_hex_with_crc(RelayControl(address, relay, status))
            # Clear the buffer after reading
            ser.reset_input_buffer()

        # Wait for a response and read it
        feedback = read_hex()
        if feedback:
            print(f"Received feedback: {feedback}")
        else:
            print("No response received.")

except KeyboardInterrupt:
    print("\nExiting...")
except serial.SerialException as e:
    print(f"Serial error: {e}")
finally:
    ser.close()  # Close the serial port