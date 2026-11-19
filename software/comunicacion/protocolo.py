"""LUMI base v1 framing. No ROS imports, usable in bench tools."""
import binascii
import json
import math
import time


def frame(boot, seq, deadline, mode, left=0, right=0):
    values = (boot, seq, deadline, mode, left, right)
    if any(type(x) is not int for x in values):
        raise ValueError("Los campos deben ser enteros")
    if not all(0 <= x <= 0xffffffff for x in (boot, seq, deadline)):
        raise ValueError("Contador fuera de uint32")
    if mode not in (0, 1, 2) or max(abs(left), abs(right)) > 200:
        raise ValueError("Modo o magnitud fuera del banco")
    if mode != 2 and (left or right):
        raise ValueError("Parada y rearme requieren magnitud cero")
    body = f"L1 {boot} {seq} {deadline} {mode} {left} {right}".encode("ascii")
    return body + f" {binascii.crc_hqx(body, 0xffff):04X}\n".encode("ascii")


def mix(linear, angular, separation, wheel_speed):
    """Open-loop duty approximation, NOT a measured wheel velocity."""
    if not all(math.isfinite(x) for x in (linear, angular, separation, wheel_speed)):
        raise ValueError("Se requieren valores finitos")
    if separation <= 0 or wheel_speed <= 0:
        raise ValueError("Falta medir geometría y velocidad de referencia")
    left = (linear - angular * separation / 2) / wheel_speed
    right = (linear + angular * separation / 2) / wheel_speed
    scale = max(1.0, abs(left) / 0.2, abs(right) / 0.2)
    return round(left / scale * 1000), round(right / scale * 1000)


class Link:
    def __init__(self, port):
        import serial
        self.serial = serial.Serial(port, 115200, timeout=0, write_timeout=0.1)
        self.state = None
        self.received = 0.0
        self.seq = 0
        self.buffer = bytearray()
        self.boot = None

    def poll(self):
        self.buffer.extend(self.serial.read(8192))
        if len(self.buffer) > 16384:
            raise RuntimeError("Telemetría excesiva o sin delimitador")
        while b"\n" in self.buffer:
            raw, _, tail = self.buffer.partition(b"\n")
            self.buffer = bytearray(tail)
            try:
                state = json.loads(raw)
                if state["v"] != 1 or not all(type(state[k]) is int and 0 <= state[k] <= 0xffffffff
                                               for k in ("boot", "seq", "uptime_ms")):
                    continue
                if type(state["armed"]) is not bool or type(state["dry_run"]) is not bool:
                    continue
            except (ValueError, KeyError, TypeError):
                continue
            if self.boot is not None and state["boot"] != self.boot:
                raise RuntimeError("La ESP se reinició; se requiere iniciar y rearmar de nuevo")
            self.boot = state["boot"]
            self.state, self.received = state, time.monotonic()
            self.seq = max(self.seq, state["seq"])
        return self.state

    def fresh(self):
        return self.state is not None and time.monotonic() - self.received < 0.15

    def send(self, mode, left=0, right=0):
        if not self.fresh():
            raise RuntimeError("Sin telemetría vigente de la ESP")
        self.seq += 1
        if self.seq > 0xffffffff:
            raise RuntimeError("Secuencia agotada; reiniciar sesión")
        elapsed = int((time.monotonic() - self.received) * 1000)
        deadline = (self.state["uptime_ms"] + elapsed + 180) & 0xffffffff
        payload = frame(self.boot, self.seq, deadline, mode, left, right)
        if self.serial.write(payload) != len(payload):
            raise RuntimeError("Escritura serie incompleta")
        return self.seq

    def close(self):
        try:
            if self.fresh():
                self.send(0)
        finally:
            self.serial.close()
