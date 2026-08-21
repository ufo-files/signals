#!/usr/bin/env python3
"""Continuously summarize HackRF sweep power into one JSON record per UTC minute."""

from __future__ import annotations

import argparse
import json
import math
import os
import signal
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def utc_minute(timestamp: float | None = None) -> datetime:
    return datetime.fromtimestamp(timestamp or time.time(), timezone.utc).replace(second=0, microsecond=0)


class MinuteAccumulator:
    def __init__(self, minute: datetime, low_hz: int, high_hz: int, bin_width: int):
        self.minute = minute
        self.low_hz = low_hz
        self.high_hz = high_hz
        self.bin_width = bin_width
        self.size = math.ceil((high_hz - low_hz) / bin_width)
        self.sums = [0.0] * self.size
        self.maxima = [float("-inf")] * self.size
        self.counts = [0] * self.size
        self.rows = 0

    def add(self, row_low: int, row_width: int, powers: list[float]) -> None:
        self.rows += 1
        for offset, power in enumerate(powers):
            frequency = row_low + offset * row_width + row_width // 2
            if frequency < self.low_hz or frequency >= self.high_hz:
                continue
            index = (frequency - self.low_hz) // self.bin_width
            if 0 <= index < self.size:
                self.sums[index] += power
                self.counts[index] += 1
                self.maxima[index] = max(self.maxima[index], power)

    def record(self, threshold_db: float) -> dict:
        averages = [round(self.sums[i] / self.counts[i], 1) if self.counts[i] else None for i in range(self.size)]
        maxima = [round(self.maxima[i], 1) if self.counts[i] else None for i in range(self.size)]
        present = [value for value in averages if value is not None]
        floor = round(statistics.median(present), 1) if present else None
        active = [i for i, value in enumerate(maxima) if value is not None and floor is not None and value >= floor + threshold_db]
        detections = []
        if active:
            start = previous = active[0]
            for index in active[1:] + [None]:
                if index is not None and index == previous + 1:
                    previous = index
                    continue
                peak_index = max(range(start, previous + 1), key=lambda i: maxima[i])
                detections.append({
                    "low_hz": self.low_hz + start * self.bin_width,
                    "high_hz": min(self.high_hz, self.low_hz + (previous + 1) * self.bin_width),
                    "peak_hz": self.low_hz + peak_index * self.bin_width + self.bin_width // 2,
                    "peak_db": maxima[peak_index],
                    "above_floor_db": round(maxima[peak_index] - floor, 1),
                })
                if index is None:
                    break
                start = previous = index
        return {
            "schema": 1,
            "minute_utc": self.minute.isoformat().replace("+00:00", "Z"),
            "range_hz": [self.low_hz, self.high_hz],
            "bin_width_hz": self.bin_width,
            "noise_floor_db": floor,
            "sweep_rows": self.rows,
            "sample_counts": self.counts,
            "average_db": averages,
            "maximum_db": maxima,
            "detections": detections,
        }


class Logger:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.stop = False
        self.process: subprocess.Popen[str] | None = None
        self.accumulator = MinuteAccumulator(utc_minute(), args.low_hz, args.high_hz, args.bin_width)

    def request_stop(self, *_args) -> None:
        self.stop = True
        if self.process and self.process.poll() is None:
            self.process.terminate()

    def flush(self) -> None:
        if not any(self.accumulator.counts):
            return
        record = self.accumulator.record(self.args.threshold_db)
        day = self.accumulator.minute.strftime("%Y-%m-%d")
        path = self.args.output / "data" / self.accumulator.minute.strftime("%Y/%m") / f"{day}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(record, separators=(",", ":")) + "\n")
            output.flush()
            os.fsync(output.fileno())

    def run(self) -> int:
        command = [
            "hackrf_sweep", "-f", f"{self.args.low_hz // 1_000_000}:{self.args.high_hz // 1_000_000}",
            "-w", str(self.args.bin_width), "-l", str(self.args.lna_gain), "-g", str(self.args.vga_gain),
            "-a", "1" if self.args.amp else "0", "-n",
        ]
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=sys.stderr, text=True, bufsize=1)
        assert self.process.stdout
        for line in self.process.stdout:
            if self.stop:
                break
            now_minute = utc_minute()
            if now_minute != self.accumulator.minute:
                self.flush()
                self.accumulator = MinuteAccumulator(now_minute, self.args.low_hz, self.args.high_hz, self.args.bin_width)
            fields = [field.strip() for field in line.split(",")]
            try:
                row_low, row_high, row_width = int(fields[2]), int(fields[3]), int(fields[4])
                powers = [float(value) for value in fields[6:] if value]
            except (IndexError, ValueError):
                continue
            expected = max(0, (row_high - row_low) // row_width)
            self.accumulator.add(row_low, row_width, powers[:expected])
        self.flush()
        return self.process.wait() if not self.stop else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("/home/hackrf/signals"))
    parser.add_argument("--low-hz", type=int, default=1_595_000_000)
    parser.add_argument("--high-hz", type=int, default=1_605_000_000)
    parser.add_argument("--bin-width", type=int, default=100_000)
    parser.add_argument("--threshold-db", type=float, default=12.0)
    parser.add_argument("--lna-gain", type=int, default=24)
    parser.add_argument("--vga-gain", type=int, default=20)
    parser.add_argument("--amp", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    logger = Logger(parse_args())
    signal.signal(signal.SIGTERM, logger.request_stop)
    signal.signal(signal.SIGINT, logger.request_stop)
    raise SystemExit(logger.run())
