#!/usr/bin/env python3
'''RollJam BLE peripheral — espone GATT service per ricevere comandi dal Flipper.

Service UUID:        a07498ca-ad5b-474e-940d-16f1fbe7e8cd
Char JAM_CMD UUID:   51ff12bb-3ed8-46e5-b4f9-d64e2147ec1d (write+notify)

Comandi (write su CMD char):
  JAM_START <freq_Hz>
  JAM_STOP
  PING

Stesso effetto del daemon file-based — scrive in /tmp/jam_cmd cosi'
il daemon esistente esegue. Disaccoppia BLE da rpitx.
'''
import asyncio, logging, os
from bless import BlessServer, BlessGATTCharacteristic, GATTCharacteristicProperties, GATTAttributePermissions

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('rolljam_ble')

SVC_UUID = 'a07498ca-ad5b-474e-940d-16f1fbe7e8cd'
CMD_UUID = '51ff12bb-3ed8-46e5-b4f9-d64e2147ec1d'
CMD_FILE = '/tmp/jam_cmd'

def on_write(characteristic: BlessGATTCharacteristic, value: bytearray, **kwargs):
    cmd = value.decode('utf-8', errors='ignore').strip()
    log.info(f'WRITE: {cmd!r}')
    try:
        with open(CMD_FILE, 'w') as f:
            f.write(cmd)
    except Exception as e:
        log.error(f'write {CMD_FILE} failed: {e}')

def on_read(characteristic: BlessGATTCharacteristic, **kwargs):
    return b'rolljam-ready'

async def main():
    server = BlessServer(name='RollJam-Pi')
    server.read_request_func = on_read
    server.write_request_func = on_write
    await server.add_new_service(SVC_UUID)
    char_flags = (GATTCharacteristicProperties.read |
                  GATTCharacteristicProperties.write |
                  GATTCharacteristicProperties.notify)
    perms = GATTAttributePermissions.readable | GATTAttributePermissions.writeable
    await server.add_new_characteristic(SVC_UUID, CMD_UUID, char_flags, b'ready', perms)
    await server.start()
    log.info('=== BLE peripheral RollJam-Pi started ===')
    log.info(f'Service UUID: {SVC_UUID}')
    log.info(f'CMD char UUID: {CMD_UUID}')
    while True:
        await asyncio.sleep(60)

if __name__ == '__main__':
    asyncio.run(main())
