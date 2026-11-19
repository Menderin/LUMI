"""Integration test that refuses any firmware capable of enabling motor PWM."""
import argparse
import json
from pathlib import Path
import time
from .protocolo import Link, frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    link = Link(args.port)
    results = []

    def wait_for(predicate, timeout=2):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            state = link.poll()
            if state and predicate(state):
                return state
            time.sleep(0.005)
        raise AssertionError(f"Sin estado esperado. Último: {link.state}")

    def check(name, predicate):
        state = wait_for(predicate)
        assert state["dry_run"] and state["left_pwm"] == state["right_pwm"] == 0, state
        results.append({"case": name, "status": "pass", "state": dict(state)})

    try:
        initial = wait_for(lambda s: True)
        if initial["dry_run"] is not True:
            raise RuntimeError("Prueba rechazada: este firmware puede habilitar potencia")
        seq = link.send(0)
        check("parada", lambda s: s["seq"] >= seq and not s["armed"])
        seq = link.send(2, 100, 100)
        check("orden_sin_rearme", lambda s: s["seq"] >= seq and s["fault"] == "not_armed")
        seq = link.send(1)
        check("rearme_en_cero", lambda s: s["seq"] >= seq and s["armed"])
        seq = link.send(2, 150, -150)
        check("giro_simulado_sin_pwm", lambda s: s["seq"] >= seq and s["left"] == 150 and s["right"] == -150)
        # Replay the accepted sequence while still fresh. It must disarm.
        state = link.state
        link.serial.write(frame(link.boot, seq, (state["uptime_ms"] + 180) & 0xffffffff, 2, 150, -150))
        check("secuencia_repetida", lambda s: not s["armed"] and s["fault"] == "sequence")
        seq = link.send(1)
        check("rearme_tras_fallo", lambda s: s["seq"] >= seq and s["armed"])
        check("caducidad_sin_heartbeat", lambda s: not s["armed"] and s["fault"] == "expired")
        seq = link.send(2, 100, 100)
        check("no_rearme_automatico", lambda s: s["seq"] >= seq and s["fault"] == "not_armed")
        link.seq += 1
        link.serial.write(frame(link.boot, link.seq, (link.state["uptime_ms"] - 1000) & 0xffffffff, 1))
        check("deadline_vencido", lambda s: s["seq"] >= link.seq and s["fault"] == "stale")
        seq = link.send(1)
        check("rearme_antes_crc", lambda s: s["seq"] >= seq and s["armed"])
        link.serial.write(b"L1 0 0 0 0 0 0 0000\n")
        check("crc_invalido", lambda s: not s["armed"] and s["fault"] == "invalid")
        seq = link.send(1)
        check("rearme_antes_overflow", lambda s: s["seq"] >= seq and s["armed"])
        link.serial.write(b"x" * 140 + b"\n")
        check("trama_excesiva", lambda s: not s["armed"] and s["fault"] == "invalid")
        link.seq += 1
        link.serial.write(frame(link.boot ^ 1, link.seq, (link.state["uptime_ms"] + 180) & 0xffffffff, 1))
        check("sesion_incorrecta", lambda s: not s["armed"] and s["fault"] == "sequence")
        print(f"{len(results)} comprobaciones USB correctas, todas sin PWM")
    except Exception as exc:
        results.append({"status": "fail", "error": str(exc)})
        raise
    finally:
        try:
            link.close()
        finally:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
