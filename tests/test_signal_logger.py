#!/usr/bin/env python3
import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace


SPEC = importlib.util.spec_from_file_location("signal_logger", Path(__file__).parents[1] / "bin" / "signal-logger.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class MinuteAccumulatorTest(unittest.TestCase):
    def test_detects_peak_and_preserves_one_hundred_bins(self):
        minute = datetime(2026, 8, 21, tzinfo=timezone.utc)
        accumulator = MODULE.MinuteAccumulator(minute, 1_595_000_000, 1_605_000_000, 100_000)
        accumulator.add(1_595_000_000, int(float("100000.00")), [-80.0] * 50 + [-60.0] + [-80.0] * 49)
        record = accumulator.record(12)
        self.assertEqual(100, len(record["average_db"]))
        self.assertEqual(1_600_050_000, record["detections"][0]["peak_hz"])

    def test_flush_uses_hourly_utc_path(self):
        with TemporaryDirectory() as directory:
            args = SimpleNamespace(
                output=Path(directory), low_hz=1_595_000_000,
                high_hz=1_605_000_000, bin_width=100_000,
                threshold_db=12, lna_gain=24, vga_gain=20, amp=False,
            )
            logger = MODULE.Logger(args)
            logger.accumulator = MODULE.MinuteAccumulator(
                datetime(2026, 8, 21, 23, 42, tzinfo=timezone.utc),
                args.low_hz, args.high_hz, args.bin_width,
            )
            logger.accumulator.add(args.low_hz, args.bin_width, [-80.0] * 100)
            logger.flush()
            expected = Path(directory) / "data/2026/08/21/2026-08-21T23.jsonl"
            self.assertTrue(expected.is_file())

    def test_flush_writes_compact_significant_archive_for_detection(self):
        with TemporaryDirectory() as directory:
            args = SimpleNamespace(
                output=Path(directory), low_hz=1_595_000_000,
                high_hz=1_605_000_000, bin_width=100_000,
                threshold_db=12, lna_gain=24, vga_gain=20, amp=False,
            )
            logger = MODULE.Logger(args)
            logger.accumulator = MODULE.MinuteAccumulator(
                datetime(2026, 8, 21, 23, 42, tzinfo=timezone.utc),
                args.low_hz, args.high_hz, args.bin_width,
            )
            logger.accumulator.add(
                args.low_hz, args.bin_width, [-80.0] * 50 + [-60.0] + [-80.0] * 49,
            )
            logger.flush()
            path = Path(directory) / "significant/2026/08/21/2026-08-21T23.jsonl"
            record = __import__("json").loads(path.read_text().strip())
            self.assertEqual(1_600_050_000, record["detections"][0]["peak_hz"])
            self.assertNotIn("average_db", record)


if __name__ == "__main__":
    unittest.main()
