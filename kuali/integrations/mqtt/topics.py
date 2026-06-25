# MQTT topic constants
# Format: kuali/<device>/<id>/<measurement>

COOKER_TEMP    = "kuali/cooker/{id}/temp"
COOKER_MODE    = "kuali/cooker/{id}/mode"
COOKER_BATCH   = "kuali/cooker/{id}/batch"
CONVEYOR_SPEED = "kuali/conveyor/{id}/speed"
CONVEYOR_STATE = "kuali/conveyor/{id}/state"
LINE_STATUS    = "kuali/line/status"
ALARM          = "kuali/alarm"


def cooker_temp(cooker_id: int) -> str:
    return COOKER_TEMP.format(id=cooker_id)


def conveyor_speed(conveyor_id: int) -> str:
    return CONVEYOR_SPEED.format(id=conveyor_id)
