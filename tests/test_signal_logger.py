#!/usr/bin/env python3
import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
