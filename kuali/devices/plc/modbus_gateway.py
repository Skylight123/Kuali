"""Production Modbus gateway - requires pymodbus + pyserial.

Config diambil dari settings.py (bersumber dari .env):
    MODBUS_MODE     : 'rtu' | 'tcp' | 'simulator'
    SERIAL_PORT     : e.g. '/dev/ttyUSB0'
    SERIAL_BAUDRATE : e.g. 9600
    SERIAL_PARITY   : N | E | O
    SERIAL_STOPBITS : 1 | 2
    SERIAL_BYTESIZE : 7 | 8
    SERIAL_TIMEOUT  : seconds, default follows trial script (5)
    Modbus slave address is configured in devices/plc/registers.py
    PLC_TCP_HOST    : IP PLC (mode tcp)
    PLC_TCP_PORT    : port TCP (default 502)
"""
from __future__ import annotations

import os
from django.conf import settings

from domain.models import CookerState, ConveyorStatus
from domain.ports import IPlcGateway
from integrations.serial.transport import SerialTransport
from . import registers as R
from . import serial_monitor

try:
    from pymodbus.client import ModbusTcpClient
except ImportError:
    ModbusTcpClient = None  # type: ignore


class ModbusGateway(IPlcGateway):

    def __init__(self):
        self._unit = R.default_slave_id()
        serial_monitor.set_connecting()

        if settings.MODBUS_MODE == "tcp":
            if ModbusTcpClient is None:
                raise ImportError("pymodbus tidak terinstall. Jalankan: pip install pymodbus pyserial")
            self._client = ModbusTcpClient(
                settings.PLC_TCP_HOST,
                port=settings.PLC_TCP_PORT,
                timeout=settings.SERIAL_TIMEOUT,
            )
        else:
            self._validate_serial_port_access()
            self._client = SerialTransport(
                port=settings.SERIAL_PORT,
                baudrate=settings.SERIAL_BAUDRATE,
                timeout=settings.SERIAL_TIMEOUT,
                stopbits=settings.SERIAL_STOPBITS,
                bytesize=settings.SERIAL_BYTESIZE,
                parity=settings.SERIAL_PARITY,
            )
        try:
            connected = self._client.connect()
        except Exception as exc:
            serial_monitor.set_failed(str(exc))
            raise
        if connected:
            serial_monitor.set_connected()
        else:
            message = "Modbus client gagal connect"
            serial_monitor.set_failed(message)
            raise ConnectionError(message)

    def _validate_serial_port_access(self) -> None:
        port = settings.SERIAL_PORT
        if not os.path.exists(port):
            message = f"Serial port tidak ditemukan: {port}"
            serial_monitor.set_failed(message)
            raise ConnectionError(message)
        if not os.access(port, os.R_OK | os.W_OK):
            message = f"Permission denied: {port}. Tambahkan user service ke group dialout"
            serial_monitor.set_failed(message)
            raise ConnectionError(message)

    # ------------------------------------------------------------------
    def _ensure_ok(self, result, action: str, address: int):
        if result.isError():
            message = f"Modbus {action} error @ {address:#06x}"
            serial_monitor.set_failed(message)
            raise ConnectionError(message)
        serial_monitor.set_connected()
        return result

    def _read_holding(self, address: int, count: int = 1) -> list[int]:
        result = self._client.read_holding_registers(address, count=count, slave=self._unit)
        return self._ensure_ok(result, "read", address).registers

    def _write_holding(self, address: int, value: int) -> None:
        result = self._client.write_register(address, value, slave=self._unit)
        self._ensure_ok(result, "write", address)

    def _write_coil(self, address: int, value: int) -> None:
        result = self._client.write_coil(address, bool(int(value)), slave=self._unit)
        self._ensure_ok(result, "write coil", address)

    # ------------------------------------------------------------------
    def read_cooker(self, cooker_id: int) -> CookerState:
        raise NotImplementedError("Kuali HMI uses read_all() register snapshots for cooker state")

    def read_conveyor(self, conveyor_id: int) -> ConveyorStatus:
        raise NotImplementedError("Kuali HMI uses read_all() register snapshots for conveyor state")

    def read_all(self) -> dict:
        start = min(R.ALL_ADDRS)
        end = max(R.ALL_ADDRS)
        values = self._read_holding(start, count=end - start + 1)
        registers = {
            address: values[address - start]
            for address in R.ALL_ADDRS
        }
        return {"registers": registers, "serial_status": serial_monitor.snapshot()}

    def remote_read(self, function_code: int, address: int, quantity: int = 1) -> dict:
        function_code = int(function_code)
        address = int(address)
        quantity = max(1, int(quantity or 1))
        R.validate_remote_access(function_code, address, quantity)

        if function_code == R.READ_COIL:
            result = self._client.read_coils(address, count=quantity, slave=self._unit)
            values = [int(value) for value in self._ensure_ok(result, "read coil", address).bits[:quantity]]
        elif function_code == R.READ_DISCRETE_INPUT:
            result = self._client.read_discrete_inputs(address, count=quantity, slave=self._unit)
            values = [int(value) for value in self._ensure_ok(result, "read discrete input", address).bits[:quantity]]
        elif function_code == R.READ_HOLDING:
            result = self._client.read_holding_registers(address, count=quantity, slave=self._unit)
            values = list(self._ensure_ok(result, "read holding", address).registers)
        elif function_code == R.READ_INPUT:
            result = self._client.read_input_registers(address, count=quantity, slave=self._unit)
            values = list(self._ensure_ok(result, "read input", address).registers)
        else:
            raise ValueError("Function code bukan operasi read")

        return {
            "function_code": function_code,
            "address": address,
            "quantity": quantity,
            "values": values,
            "serial_status": serial_monitor.snapshot(),
        }

    def remote_write(self, function_code: int, address: int, values) -> dict:
        function_code = int(function_code)
        address = int(address)
        if not isinstance(values, list):
            values = [values]
        quantity = len(values)
        R.validate_remote_access(function_code, address, quantity)

        if function_code == R.WRITE_SINGLE_COIL:
            result = self._client.write_coil(address, bool(int(values[0])), slave=self._unit)
        elif function_code == R.WRITE_SINGLE_REGISTER:
            result = self._client.write_register(address, int(values[0]), slave=self._unit)
        elif function_code == R.WRITE_MULTIPLE_COIL:
            result = self._client.write_coils(address, [bool(int(value)) for value in values], slave=self._unit)
        elif function_code == R.WRITE_MULTIPLE_REGISTER:
            result = self._client.write_registers(address, [int(value) for value in values], slave=self._unit)
        else:
            raise ValueError("Function code bukan operasi write")

        self._ensure_ok(result, "write", address)
        return {
            "function_code": function_code,
            "address": address,
            "quantity": quantity,
            "values": [int(value) for value in values],
            "serial_status": serial_monitor.snapshot(),
        }

    def write_register(self, address: int, value: int) -> None:
        R.validate_remote_access(R.WRITE_SINGLE_REGISTER, address, 1)
        self._write_holding(address, value)

    def write_command(self, address: int, value: int) -> None:
        R.validate_remote_access(R.WRITE_SINGLE_COIL, address, 1)
        self._write_coil(address, value)

    def close(self) -> None:
        self._client.close()
