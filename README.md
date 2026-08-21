# HackRF Signal Archive

Continuous spectrum summaries from a HackRF One dedicated to 1595–1605 MHz.

Each JSONL record describes one UTC minute at 100 kHz resolution:

- average and maximum power for every bin;
- an adaptive median noise floor;
- contiguous detections at least 12 dB above that floor;
- sample counts and sweep-row counts for coverage auditing.

Completed UTC days are committed to `data/YYYY/MM/YYYY-MM-DD.jsonl` shortly
after 00:10 UTC. The current day stays local until it is complete. Raw IQ and
audio are deliberately not recorded.

## Operations

```sh
systemctl status hackrf-signal-logger.service
systemctl status hackrf-signal-publish.timer
journalctl -u hackrf-signal-logger.service
```

OpenWebRX is disabled because the HackRF supports only one active receiver
process. To restore OpenWebRX, stop and disable `hackrf-signal-logger.service`
before enabling `openwebrx.service`.
Daily HackRF signal and operational logs
