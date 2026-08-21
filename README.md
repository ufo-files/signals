# HackRF Signal Archive

Continuous spectrum summaries from a HackRF One dedicated to 1595–1605 MHz.

Each JSONL record describes one UTC minute at 100 kHz resolution:

- average and maximum power for every bin;
- an adaptive median noise floor;
- contiguous detections at least 12 dB above that floor;
- sample counts and sweep-row counts for coverage auditing.

The active and queued files live outside the Git checkout in
`/home/hackrf/signal-spool/data/YYYY/MM/DD/YYYY-MM-DDTHH.jsonl`. Shortly after
10 minutes past every UTC hour, each completed hour is published oldest-first
on its own branch and merged through a GitHub pull request. The publisher
fetches `origin/main` and verifies the merged file's SHA-256 before deleting its
local spool copy. A network, authentication, push, or merge failure leaves the
local file untouched; later hours continue logging and the next timer run
retries the full backlog. Raw IQ and audio are deliberately not recorded.

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
