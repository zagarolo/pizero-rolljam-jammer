#!/usr/bin/env python3
'''Scanner BLE passivo per beacon RollJam dal Flipper Zero.

Il FAP rolljam_dual.fap pubblica advertising con mfg_data:
  bytes 0-3 = magic 'RJ01'
  byte 4    = stato (0=OFF, 1=ON_433, 2=ON_868)

Quando rileva ON → scrive JAM_START al daemon.
Quando rileva OFF → scrive JAM_STOP.
'''
import asyncio, time, os, logging
from bleak import BleakScanner

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('rj-scan')

CMD_FILE = '/tmp/jam_cmd'
MAGIC = bytes([0x52, 0x4A, 0x30, 0x31])  # 'RJ01'
STATE_OFF, STATE_ON_433, STATE_ON_868 = 0x00, 0x01, 0x02

last_state = STATE_OFF

def write_cmd(cmd: str):
    try:
        with open(CMD_FILE, 'w') as f:
            f.write(cmd)
        os.chmod(CMD_FILE, 0o666)
        log.info(f'CMD → {cmd}')
    except Exception as e:
        log.error(f'write fail: {e}')

def parse_data(d: bytes):
    if len(d) < 5: return None
    if d[:4] != MAGIC: return None
    return d[4]

def on_advertisement(device, adv_data):
    if adv_data.manufacturer_data:
        for cid,val in adv_data.manufacturer_data.items():
            log.info(f"ADV {device.address} cid={cid:04x} data={bytes(val).hex()}")
    global last_state
    # mfg_data dict {company_id: bytes}; cerca anche service_data
    candidates = []
    for cid, val in (adv_data.manufacturer_data or {}).items():
        candidates.append(bytes(val))
    for k, v in (adv_data.service_data or {}).items():
        candidates.append(bytes(v))
    # Anche raw advertisement, talvolta data direttamente in adv
    if hasattr(adv_data, 'platform_data') and adv_data.platform_data:
        for c in adv_data.platform_data:
            if isinstance(c, (bytes, bytearray)):
                candidates.append(bytes(c))
    for blob in candidates:
        # Cerca magic ovunque nel blob (alcuni stack mettono header company id)
        idx = blob.find(MAGIC)
        if idx >= 0 and idx + 4 < len(blob):
            state = blob[idx + 4]
            if state != last_state:
                last_state = state
                if state == STATE_ON_433:
                    write_cmd('JAM_START 433920000')
                elif state == STATE_ON_868:
                    write_cmd('JAM_START 868000000')
                elif state == STATE_OFF:
                    write_cmd('JAM_STOP')
            return

async def main():
    log.info('=== RollJam beacon scanner START ===')
    scanner = BleakScanner(on_advertisement)
    await scanner.start()
    while True:
        await asyncio.sleep(60)

if __name__ == '__main__':
    asyncio.run(main())
