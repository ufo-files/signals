#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

install -m 0755 "$ROOT/bin/signal-logger.py" /usr/local/libexec/hackrf-signal-logger
install -m 0755 "$ROOT/bin/publish-daily.sh" /usr/local/libexec/hackrf-signal-publish
install -m 0644 "$ROOT/systemd/hackrf-signal-logger.service" /etc/systemd/system/hackrf-signal-logger.service
install -m 0644 "$ROOT/systemd/hackrf-signal-publish.service" /etc/systemd/system/hackrf-signal-publish.service
install -m 0644 "$ROOT/systemd/hackrf-signal-publish.timer" /etc/systemd/system/hackrf-signal-publish.timer
install -d -o hackrf -g hackrf -m 0750 /home/hackrf/signal-spool

if [ -d /home/hackrf/signals/data ]; then
  cp -a /home/hackrf/signals/data /home/hackrf/signal-spool/
  chown -R hackrf:hackrf /home/hackrf/signal-spool/data
fi

systemctl disable --now openwebrx.service
systemctl daemon-reload
systemctl enable hackrf-signal-logger.service hackrf-signal-publish.timer
systemctl restart hackrf-signal-logger.service
systemctl restart hackrf-signal-publish.timer

echo "Continuous logger and daily publisher installed."
