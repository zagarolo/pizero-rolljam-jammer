#!/usr/bin/env python3
"""RollJam bridge — orchestratore Flipper Zero ↔ Pi Zero 2W.

Monitora il debug log del FAP Flipper via flipwire BLE, e quando il
FAP entra in ATTACK START → invia JAM_START al Pi Zero via BLE.
Quando il FAP termina (ATTACK DONE / radio_deinit), invia JAM_STOP.

Architettura distribuita:
  Flipper FAP  ──BLE──►  Pi5 (questo bridge)  ──BLE──►  Pi Zero (rpitx jam)

Uso:
  python3 rolljam_bridge.py              # default 433.92 MHz
  python3 rolljam_bridge.py 868000000    # custom freq
"""
import asyncio, subprocess, sys, time, re
from pathlib import Path

FLIPPER_NAME = "Omoon"                          # nome Flipper per flipwire
FLIPPER_LOG  = "/ext/subghz/rolljam/debug.log"
LOCAL_LOG    = "/tmp/flipper_attack.log"

PI_ZERO_MAC  = "B8:27:EB:61:2F:DD"
CMD_CHAR_UUID = "51ff12bb-3ed8-46e5-b4f9-d64e2147ec1d"

JAM_FREQ_HZ  = int(sys.argv[1]) if len(sys.argv) > 1 else 433920000

FLIPWIRE = "/home/pi/rf_tools/flipwire/target/release/flipwire"

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

async def send_pi_cmd(cmd: str):
    """Invia comando BLE al Pi Zero peripheral."""
    from bleak import BleakClient
    try:
        async with BleakClient(PI_ZERO_MAC, timeout=10) as cli:
            await cli.write_gatt_char(CMD_CHAR_UUID, cmd.encode(), response=False)
            log(f"BLE → Pi Zero: {cmd}")
    except Exception as e:
        log(f"BLE send FAIL: {e}")

def fetch_flipper_log() -> str:
    """Scarica debug.log dal Flipper via flipwire."""
    try:
        r = subprocess.run(
            [FLIPWIRE, "-f", FLIPPER_NAME, "-d", "download", FLIPPER_LOG, LOCAL_LOG],
            capture_output=True, timeout=15
        )
        if r.returncode == 0 and Path(LOCAL_LOG).exists():
            return Path(LOCAL_LOG).read_text(errors="ignore")
    except Exception as e:
        log(f"flipwire download fail: {e}")
    return ""

async def main():
    log("=== RollJam bridge START ===")
    log(f"Jam freq: {JAM_FREQ_HZ} Hz")
    log(f"Pi Zero peripheral: {PI_ZERO_MAC}")

    last_state = "IDLE"  # IDLE / JAMMING

    while True:
        text = fetch_flipper_log()
        if text:
            # Cerca evento più recente
            attack_started = "=== ATTACK START ===" in text
            attack_done = ("ATTACK DONE" in text or "radio_deinit done" in text)

            new_state = last_state
            if attack_started and not attack_done:
                new_state = "JAMMING"
            elif attack_done:
                new_state = "IDLE"

            if new_state != last_state:
                log(f"State change: {last_state} → {new_state}")
                if new_state == "JAMMING":
                    await send_pi_cmd(f"JAM_START {JAM_FREQ_HZ}")
                else:
                    await send_pi_cmd("JAM_STOP")
                last_state = new_state

        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
