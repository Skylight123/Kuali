# Modbus register map - sesuaikan nomor alamat dengan PLC aktual.
# Semua nilai address di bawah mengikuti address yang dipakai program Kuali.
# Jika PLC kamu memakai display base-0/base-1 berbeda, sesuaikan nilai di sini.

# --- Status (read) ---
STIRRER_1   = 1    # 0=off  1=on
STIRRER_2   = 2    # 0=off  1=on

CONVEYOR_1  = 3    # mie       - 0=stop 1=jalan
CONVEYOR_2  = 4    # sauce 1
CONVEYOR_3  = 5    # sauce 2
CONVEYOR_4  = 6    # topping 1
CONVEYOR_5  = 7    # topping 2
CONVEYOR_6  = 8    # topping 3

# --- Perintah (write coil / FC05 sesuai trial_modbusclient.py) ---
CMD_9       = 9    # perintah stirrer 1
CMD_10      = 10   # perintah stirrer 2

# --- Status ready PLC (read) ---
CMD_11      = 11   # status ON/ready PLC utama; sumber feedback error broker

# Semua address dalam satu list (untuk bulk read HMI utama)
STATUS_ADDRS  = [STIRRER_1, STIRRER_2,
                 CONVEYOR_1, CONVEYOR_2, CONVEYOR_3,
                 CONVEYOR_4, CONVEYOR_5, CONVEYOR_6,
                 CMD_11]
COMMAND_ADDRS = [CMD_9, CMD_10]
COMMAND_COIL_ADDRS = COMMAND_ADDRS
SCANNER_COIL_START = 80
SCANNER_COIL_QUANTITY = 10
SCANNER_COIL_ADDRS = list(range(SCANNER_COIL_START, SCANNER_COIL_START + SCANNER_COIL_QUANTITY))
ALL_ADDRS = sorted(set(STATUS_ADDRS + COMMAND_ADDRS))

# --- Modbus function code configuration ---
READ_COIL = 1
READ_DISCRETE_INPUT = 2
READ_HOLDING = 3
READ_INPUT = 4
WRITE_SINGLE_COIL = 5
WRITE_SINGLE_REGISTER = 6
WRITE_MULTIPLE_COIL = 15
WRITE_MULTIPLE_REGISTER = 16

# --- Modbus slave / unit address configuration ---
# Ubah slave_id di sini jika PLC memakai Modbus address lain.
# Untuk upgrade multiple slave, tambah entry baru, misalnya:
#   "drink_plc": {"slave_id": 2, "label": "PLC Minuman"}
MODBUS_SLAVES = {
    "main_plc": {"slave_id": 1, "label": "PLC Utama - Stirrer"},
}
DEFAULT_MODBUS_SLAVE = "main_plc"


def default_slave_id() -> int:
    return int(MODBUS_SLAVES[DEFAULT_MODBUS_SLAVE]["slave_id"])


def slave_options() -> list[dict]:
    return [
        {"key": key, **value}
        for key, value in MODBUS_SLAVES.items()
    ]

MODBUS_FUNCTIONS = {
    READ_COIL: {
        "name": "read_coil",
        "label": "01 Read Coil",
        "operation": "read",
        "table": "coil",
    },
    READ_DISCRETE_INPUT: {
        "name": "read_discrete_input",
        "label": "02 Read Discrete Input",
        "operation": "read",
        "table": "discrete_input",
    },
    READ_HOLDING: {
        "name": "read_holding",
        "label": "03 Read Holding Register",
        "operation": "read",
        "table": "holding_register",
    },
    READ_INPUT: {
        "name": "read_input",
        "label": "04 Read Input Register",
        "operation": "read",
        "table": "input_register",
    },
    WRITE_SINGLE_COIL: {
        "name": "write_single_coil",
        "label": "05 Write Single Coil",
        "operation": "write",
        "table": "coil",
        "multiple": False,
    },
    WRITE_SINGLE_REGISTER: {
        "name": "write_single_register",
        "label": "06 Write Single Register",
        "operation": "write",
        "table": "holding_register",
        "multiple": False,
    },
    WRITE_MULTIPLE_COIL: {
        "name": "write_multiple_coil",
        "label": "15 Write Multiple Coil",
        "operation": "write",
        "table": "coil",
        "multiple": True,
    },
    WRITE_MULTIPLE_REGISTER: {
        "name": "write_multiple_register",
        "label": "16 Write Multiple Register",
        "operation": "write",
        "table": "holding_register",
        "multiple": True,
    },
}

# Address yang boleh diremote dari tab Modbus Slave.
# Command utama memakai coil supaya sama dengan kuali/trial/trial_modbusclient.py.
# Address 80-89 dibuka read-only untuk pola scanner serial yang membaca coil batch.
COIL_ADDRS = COMMAND_COIL_ADDRS + SCANNER_COIL_ADDRS
DISCRETE_INPUT_ADDRS = []
HOLDING_ADDRS = ALL_ADDRS
INPUT_ADDRS = []

WRITABLE_COIL_ADDRS = COMMAND_COIL_ADDRS
WRITABLE_HOLDING_ADDRS = COMMAND_ADDRS

MODBUS_ALLOWED_ADDRESSES = {
    READ_COIL: COIL_ADDRS,
    READ_DISCRETE_INPUT: DISCRETE_INPUT_ADDRS,
    READ_HOLDING: HOLDING_ADDRS,
    READ_INPUT: INPUT_ADDRS,
    WRITE_SINGLE_COIL: WRITABLE_COIL_ADDRS,
    WRITE_SINGLE_REGISTER: WRITABLE_HOLDING_ADDRS,
    WRITE_MULTIPLE_COIL: WRITABLE_COIL_ADDRS,
    WRITE_MULTIPLE_REGISTER: WRITABLE_HOLDING_ADDRS,
}

MODBUS_DEFAULT_FUNCTION = READ_HOLDING
MODBUS_DEFAULT_ADDRESS = STIRRER_1
MODBUS_DEFAULT_QUANTITY = 10
MODBUS_MAX_QUANTITY = 100


def function_options() -> list[dict]:
    return [
        {"code": code, **config}
        for code, config in MODBUS_FUNCTIONS.items()
    ]


def allowed_addresses(function_code: int) -> list[int]:
    return list(MODBUS_ALLOWED_ADDRESSES.get(int(function_code), []))


def validate_remote_access(function_code: int, address: int, quantity: int = 1) -> None:
    code = int(function_code)
    if code not in MODBUS_FUNCTIONS:
        raise ValueError(f"Function code {code} belum dikonfigurasi")

    quantity = max(1, int(quantity or 1))
    if quantity > MODBUS_MAX_QUANTITY:
        raise ValueError(f"Quantity maksimal {MODBUS_MAX_QUANTITY}")

    allowed = set(allowed_addresses(code))
    requested = set(range(int(address), int(address) + quantity))
    if not requested.issubset(allowed):
        raise ValueError("Address belum diizinkan di devices/plc/registers.py")
