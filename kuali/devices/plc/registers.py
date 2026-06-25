# Modbus register map — sesuaikan nomor alamat dengan PLC aktual
# Semua nilai adalah Modbus holding-register address (basis 1, Modbus convention)

# --- Status (read) ---
STIRRER_1   = 1    # 0=off  1=on
STIRRER_2   = 2    # 0=off  1=on

CONVEYOR_1  = 3    # mie       — 0=stop 1=jalan
CONVEYOR_2  = 4    # sauce 1
CONVEYOR_3  = 5    # sauce 2
CONVEYOR_4  = 6    # topping 1
CONVEYOR_5  = 7    # topping 2
CONVEYOR_6  = 8    # topping 3

# --- Perintah (write) ---
CMD_9       = 9    # perintah stirrer 1 / recipe command, sesuai mapping PLC
CMD_10      = 10   # perintah stirrer 2 / recipe command, sesuai mapping PLC

# --- Status ready PLC (read) ---
CMD_11      = 11   # status ON/ready PLC utama; sumber feedback error broker

# Semua address dalam satu list (untuk bulk read)
STATUS_ADDRS  = [STIRRER_1, STIRRER_2,
                 CONVEYOR_1, CONVEYOR_2, CONVEYOR_3,
                 CONVEYOR_4, CONVEYOR_5, CONVEYOR_6,
                 CMD_11]
COMMAND_ADDRS = [CMD_9, CMD_10]
ALL_ADDRS = sorted(set(STATUS_ADDRS + COMMAND_ADDRS))
