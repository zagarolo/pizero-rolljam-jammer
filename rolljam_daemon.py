#!/usr/bin/env python3
'''RollJam daemon — controlla rpitx via comandi in /tmp/jam_cmd
Comandi:
  JAM_START <freq_Hz>   — avvia TX OOK carrier continuo
  JAM_STOP              — ferma TX
  PING                  — health check (log)
'''
import os, subprocess, time, signal

CMD_FILE = '/tmp/jam_cmd'
LOG_FILE = '/tmp/rolljam_daemon.log'
RPITX_BIN = '/home/pizero/rpitx/sendiq'
TX_PROC = None

def log(msg):
    with open(LOG_FILE, 'a') as f:
        f.write(f'{time.strftime("%H:%M:%S")} {msg}\n')
    print(msg, flush=True)

def jam_start(freq_hz):
    global TX_PROC
    jam_stop()
    # Generate continuous IQ sample (DC = carrier) to rpitx
    # sendiq: -s samplerate -f freq
    log(f'JAM_START {freq_hz} Hz')
    # Simple approach: use pichirp (minimal CW-like)
    TX_PROC = subprocess.Popen(
        ['sudo', '/home/pizero/rpitx/tune', '-f', str(freq_hz)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def jam_fsk_start(freq_hz):
    global TX_PROC
    jam_stop()
    log(f'JAM_FSK {freq_hz} Hz (tune CW fallback, no sweep → no falsi trigger)')
    TX_PROC = subprocess.Popen(
        ['sudo', '/home/pizero/rpitx/tune', '-f', str(freq_hz)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

def jam_stop():
    global TX_PROC
    if TX_PROC and TX_PROC.poll() is None:
        log('JAM_STOP — killing')
        TX_PROC.terminate()
        try: TX_PROC.wait(timeout=2)
        except: TX_PROC.kill()
    TX_PROC = None
    subprocess.run(['sudo', 'pkill', '-9', 'tune'], capture_output=True)
    subprocess.run(['sudo', 'pkill', '-9', 'sendiq'], capture_output=True)
    subprocess.run(['sudo', 'pkill', '-9', 'rpitx'], capture_output=True)
    # Fix GPIO4 residual GPCLK0 output after kill
    subprocess.run(['sudo', 'raspi-gpio', 'set', '4', 'ip'], capture_output=True)

def process_cmd(cmd):
    parts = cmd.strip().split()
    if not parts: return
    c = parts[0].upper()
    if c == 'JAM_START' and len(parts) >= 2:
        try: freq = int(parts[1])
        except: return
        jam_start(freq)
    elif c == 'JAM_FSK' and len(parts) >= 2:
        try: freq = int(parts[1])
        except: return
        jam_fsk_start(freq)
    elif c == 'JAM_STOP':
        jam_stop()
    elif c == 'PING':
        log('PING received')

def main():
    log('=== RollJam daemon START ===')
    signal.signal(signal.SIGTERM, lambda *a: (jam_stop(), exit(0)))
    last_cmd = ''
    while True:
        try:
            if os.path.exists(CMD_FILE):
                with open(CMD_FILE) as f:
                    cmd = f.read().strip()
                if cmd and cmd != last_cmd:
                    last_cmd = cmd
                    process_cmd(cmd)
                    os.remove(CMD_FILE)
            # WATCHDOG: se TX attivo da >15s senza nuovi comandi → auto-kill
            if TX_PROC and TX_PROC.poll() is None and (time.time() - JAM_START_T) > 15.0:
                log('WATCHDOG: TX running >15s no cmd, auto-kill')
                jam_stop()
                last_cmd = ''
        except Exception as e:
            log(f'ERR {e}')
        time.sleep(0.1)

if __name__ == '__main__':
    main()
