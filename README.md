# Pi Zero 2W RollJam Jammer Daemon

Daemon Python che gira su Raspberry Pi Zero 2W per pilotare `rpitx` come jammer RF 433.92 MHz su comando remoto (file IPC, in futuro BLE).

## Architettura

Sistema RollJam distribuito a due dispositivi:

```
[Auto vittima] ←3m→ [Flipper Zero + CC1101 RX] ←BLE 10m→ [Pi Zero 2W + rpitx TX]
                         (cattura keyfob)                  (jam continuo 433.92)
```

Risolve limite hardware su single chip (jam+RX simultanei impossibili per SPI conflict + antenna coupling desensing).

## Hardware

- Raspberry Pi Zero 2W
- PiSugar batteria + magnete (montaggio remoto)
- Antenna 433 MHz su GPIO4 (FPC flat MHF4 + adapter SMA, oppure helical spring)

## Setup

```bash
# Install rpitx
git clone https://github.com/F5OEO/rpitx.git
cd rpitx && ./install.sh

# Sudoers NOPASSWD (vedi systemd_service_and_sudoers.txt)
sudo visudo -f /etc/sudoers.d/rolljam-rpitx

# Daemon + systemd service
cp rolljam_daemon.py /home/pizero/
sudo cp systemd_service_and_sudoers.txt /tmp/  # split manualmente
sudo systemctl enable --now rolljam-daemon
```

## Comandi (via /tmp/jam_cmd)

| Comando | Effetto |
|---|---|
| `JAM_START <freq_Hz>` | avvia TX OOK carrier su frequenza |
| `JAM_STOP` | ferma TX |
| `PING` | health check (log) |

Esempio:
```bash
echo "JAM_START 433920000" > /tmp/jam_cmd
sleep 5
echo "JAM_STOP" > /tmp/jam_cmd
```

## Roadmap

- [x] v1: file-based IPC (`/tmp/jam_cmd`)
- [ ] v2: BLE peripheral GATT, Flipper come central
- [ ] v3: protocollo bidirezionale con ack
