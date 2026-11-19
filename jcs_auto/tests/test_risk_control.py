# -*- coding: utf-8 -*-
"""risk_control + scheduler 单元测试"""
import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from risk_control import RiskControl
from scheduler import DailyScheduler


class TestRiskControl(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()) / "state.json"
        self.rc = RiskControl(state_path=self.tmp)

    def test_frequency_daily_limit(self):
        # 用动态"今天"：record_result 以真实系统时间写 last_date，
        # 检查日期必须与之一致，否则跨天后该用例会误挂（时间耦合缺陷修复）
        now = dt.datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        self.rc.record_result("a1", True)
        ok, msg = self.rc.check_frequency("a1", now)
        self.assertFalse(ok)
        self.assertIn("今天已发布", msg)

    def test_window_hours(self):
        ok, msg = self.rc.check_frequency("a2", dt.datetime(2026, 10, 27, 8, 0))
        self.assertFalse(ok)
        self.assertIn("非发布时段", msg)

    def test_suspension(self):
        self.rc.suspend("a3", "触发验证码", hours=3)
        ok, msg = self.rc.check_suspension("a3", dt.datetime.now() + dt.timedelta(minutes=1))
        self.assertFalse(ok)
        self.assertIn("冷却", msg)

    def test_copy_similarity(self):
        ok, _ = self.rc.check_copy("今天天气真好", ["今天天气真不错"])
        self.assertFalse(ok)
        ok2, _ = self.rc.check_copy("完全不同的内容", ["另一篇毫无关系"])
        self.assertTrue(ok2)

    def test_fail_rate_fuse(self):
        self.rc.record_result("a4", False, "网络错误")
        self.rc.record_result("a4", False, "网络错误")
        self.rc.record_result("a4", False, "网络错误")
        ok, msg = self.rc.check_suspension("a4", dt.datetime.now())
        self.assertFalse(ok)


class TestScheduler(unittest.TestCase):
    def _mk(self, n):
        s = DailyScheduler.__new__(DailyScheduler)
        s.accounts = [{"id": f"a{i}"} for i in range(1, n + 1)]
        s.publish_each, s.day_start, s.day_end = 1, 9, 22
        return s

    def test_schedule_gaps(self):
        s = self._mk(5)
        queue = s.build_schedule(dt.date(2026, 10, 27))
        times = [dt.datetime.fromisoformat(q["publish_time"]) for q in queue]
        times.sort()
        self.assertEqual(len(times), 5)
        for a, b in zip(times, times[1:]):
            self.assertGreaterEqual((b - a).total_seconds() / 60, 30)

    def test_15_accounts_all_gap_ok(self):
        s = self._mk(15)
        queue = s.build_schedule(dt.date(2026, 10, 27))
        times = sorted(dt.datetime.fromisoformat(q["publish_time"]) for q in queue)
        self.assertEqual(len(times), 15)
        for a, b in zip(times, times[1:]):
            self.assertGreaterEqual((b - a).total_seconds() / 60, 30)
        # 都在 9:00-22:00 内
        for t in times:
            self.assertGreaterEqual(t.hour, 9)
            self.assertLess(t.hour, 22)

    def test_too_many_raises(self):
        s = self._mk(80)  # 80 条 > 窗口容量
        with self.assertRaises(ValueError):
            s.build_schedule(dt.date(2026, 10, 27))


if __name__ == "__main__":
    unittest.main()
