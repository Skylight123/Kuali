# Modbus register map — sesuaikan dengan register PLC aktual
# Format: NAMA = alamat (int, basis 0)

# --- Cooker 1 ---
C1_TEMP_PV      = 0x0100   # current temperature (×10, e.g. 2250 = 225.0 °C)
C1_TEMP_SP      = 0x0101   # setpoint temperature
C1_MODE         = 0x0102   # 0=idle 1=heating 2=cooking 3=fault
C1_BATCH        = 0x0103   # 0=empty 1=loading 2=cooking 3=done
C1_PROGRESS     = 0x0104   # 0–100 %
C1_RUNTIME      = 0x0105   # seconds in current batch
C1_FAULT_CODE   = 0x0106

# --- Cooker 2 ---
C2_TEMP_PV      = 0x0110
C2_TEMP_SP      = 0x0111
C2_MODE         = 0x0112
C2_BATCH        = 0x0113
C2_PROGRESS     = 0x0114
C2_RUNTIME      = 0x0115
C2_FAULT_CODE   = 0x0116

# --- Conveyor 1 ---
CV1_STATE       = 0x0200   # 0=stopped 1=running 2=fault
CV1_SPEED       = 0x0201   # 0–100 %
CV1_LOAD        = 0x0202
CV1_FAULT       = 0x0203

# --- Conveyor 2 ---
CV2_STATE       = 0x0210
CV2_SPEED       = 0x0211
CV2_LOAD        = 0x0212
CV2_FAULT       = 0x0213

# --- Conveyor 3 ---
CV3_STATE       = 0x0220
CV3_SPEED       = 0x0221
CV3_LOAD        = 0x0222
CV3_FAULT       = 0x0223

# --- Line control ---
LINE_MODE       = 0x0300   # 0=manual 1=auto
LINE_ESTOP      = 0x0301   # 0=normal 1=e-stop active
