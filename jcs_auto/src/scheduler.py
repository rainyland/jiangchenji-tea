# -*- coding: utf-8 -*-
"""
scheduler.py — 每日发布队列调度
职责：
  1. 读配置（账号清单、时段窗口、每日条数）
  2. 为每账号分配当天发布时间（错开 ≥30 分钟）
  3. 按时间生成待执行队列；到点执行时由 risk_control 二次校验
"""
import datetime as dt
import json
import random
from pathlib import Path

MIN_GAP_MIN = 30     # 账号间最小间隔（与风控一致）
DAY_START, DAY_END = 9, 22


class DailyScheduler:
    def __init__(self, config_path: str | Path):
        cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
        self.accounts = cfg["accounts"]               # [{id, name, proxy, env}]
        self.publish_each = cfg.get("publish_each", 1)  # 每账号每日条数（默认1）
        self.day_start = cfg.get("day_start", DAY_START)
        self.day_end = cfg.get("day_end", DAY_END)
        # 集中发布窗口（可选）：{"start": 10, "duration": 60} = 10:00-11:00 集中发完
        # 配置后覆盖全天分散模式，改为小窗口内均匀分布（人工流水线操作）
        self.batch_window = cfg.get("batch_window")   # 如 {"start": 10, "duration": 60}

    def build_schedule(self, date: dt.date | None = None) -> list[dict]:
        """为当日所有账号分配发布时间。
        两种模式：
        - 集中窗口（配了 batch_window）：小窗口内均匀分布，人工流水线 1 小时发完
        - 全天分散（默认）：大窗口内错峰 ≥30 分钟
        """
        date = date or dt.date.today()
        n = len(self.accounts)
        if n == 0:
            return []
        total_slots = self.publish_each * n
        rng = random.Random(int(date.strftime("%Y%m%d")))

        if getattr(self, "batch_window", None):
            # 集中模式：小窗口内均匀分布，间隔 = 窗口/条数
            bw = self.batch_window
            win_start = bw.get("start", 10)
            win_dur = bw.get("duration", 60)
            segment = win_dur / total_slots
            d = max(0, int(segment / 4))   # 抖动幅度 = 间隔的 1/4，避免太整齐
            slots = []
            for i in range(total_slots):
                base = win_start * 60 + (i + 0.5) * segment
                t = int(base + rng.randint(-d, d))
                slots.append(t)
        else:
            # 全天分散模式：大窗口内错峰 ≥30 分钟
            window_min = (self.day_end - self.day_start) * 60
            segment = window_min / total_slots
            if segment < MIN_GAP_MIN:
                raise ValueError(
                    f"发布窗口 {window_min} 分钟 / {total_slots} 条 < 最小间隔 {MIN_GAP_MIN} 分钟，"
                    f"请减少账号或扩大 day_start/day_end 窗口")
            d = max(0, int((segment - MIN_GAP_MIN) / 2))
            slots = []
            for i in range(total_slots):
                base = self.day_start * 60 + (i + 0.5) * segment
                t = int(base + rng.randint(-d, d))
                slots.append(t)
        slots.sort()

        queue = []
        idx = 0
        for acc in self.accounts:
            for _ in range(self.publish_each):
                mins = slots[idx]
                idx += 1
                queue.append({
                    "account": acc["id"],
                    "name": acc.get("name", acc["id"]),
                    "publish_time": dt.datetime(date.year, date.month, date.day,
                                                mins // 60, mins % 60).isoformat(),
                })
        # 按发布时间排序输出
        queue.sort(key=lambda x: x["publish_time"])
        return queue

    def due_tasks(self, queue: list[dict], now: dt.datetime | None = None) -> list[dict]:
        """过滤出到点该执行的队列项（供主循环消费）"""
        now = now or dt.datetime.now()
        return [q for q in queue if dt.datetime.fromisoformat(q["publish_time"]) <= now]


if __name__ == "__main__":
    s = DailyScheduler(Path(__file__).parent.parent / "config" / "config.example.json")
    for item in s.build_schedule():
        print(item["name"], "→", dt.datetime.fromisoformat(item["publish_time"]).strftime("%H:%M"))
