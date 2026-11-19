# -*- coding: utf-8 -*-
"""
risk_control.py — 风控规则引擎（贯穿全链路）
职责：
  1. 频率校验：每账号每日 ≤1 条、相邻账号发布间隔 ≥30 分钟
  2. 图片去重：发布前 hash 校验（引用 asset_lib）
  3. 文案相似度：同批账号文案相似度 <60%（SequenceMatcher）
  4. 熔断管理：验证码/失败率/违规 → 停号并记录
  5. 调度校验：时段窗口（9:00-22:00）、账号冷却状态
"""
import datetime as dt
import json
import os
from pathlib import Path

from difflib import SequenceMatcher

MIN_INTERVAL_MIN = 30          # 相邻账号发布最小间隔（分钟）
DAILY_LIMIT = 1                # 每账号每日上限（条）
WINDOW = (9, 22)               # 发布时段 9:00-22:00
FAIL_RATE_LIMIT = 0.20         # 失败率熔断阈值
COOLDOWN_HOURS = 3             # 验证码等异常冷却时长（小时）

STATE_FILE = "state.json"      # 运行状态（每日调度/冷却/熔断）


class RiskControl:
    def __init__(self, state_path: str | Path | None = None, asset_lib=None):
        self.state_path = Path(state_path) if state_path else Path("output/logs/state.json")
        self.asset_lib = asset_lib
        self.state = self._load()

    # ---------- 状态持久化 ----------
    def _load(self) -> dict:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {"accounts": {}, "published_today": [], "suspensions": {}}

    def _save(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- 频率与时段 ----------
    def check_frequency(self, account: str, now: dt.datetime | None = None) -> tuple[bool, str]:
        """检查账号今天是否已发满、是否在可发布时段"""
        now = now or dt.datetime.now()
        today = now.strftime("%Y-%m-%d")
        acc = self.state["accounts"].get(account, {})
        if acc.get("last_date") == today:
            return False, f"{account} 今天已发布（每日上限 {DAILY_LIMIT} 条）"
        hour = now.hour
        if not (WINDOW[0] <= hour < WINDOW[1]):
            return False, f"非发布时段（{WINDOW[0]}:00-{WINDOW[1]}:00）"
        return True, "ok"

    def check_suspension(self, account: str, now: dt.datetime | None = None) -> tuple[bool, str]:
        """检查账号是否处于冷却/熔断状态"""
        now = now or dt.datetime.now()
        sus = self.state["suspensions"].get(account)
        if not sus:
            return True, "ok"
        until = dt.datetime.fromisoformat(sus["until"])
        if now < until:
            return False, f"{account} 冷却中，至 {until:%H:%M}（原因：{sus['reason']}）"
        # 冷却到期，清除
        del self.state["suspensions"][account]
        self._save()
        return True, "ok"

    # ---------- 账号间间隔 ----------
    def check_interval(self, account: str, now: dt.datetime | None = None) -> tuple[bool, str]:
        """相邻账号发布时间间隔 ≥30 分钟（错峰）"""
        now = now or dt.datetime.now()
        last = self.state["published_today"]
        if last:
            last_dt = dt.datetime.fromisoformat(last[-1]["time"])
            gap = (now - last_dt).total_seconds() / 60
            if gap < MIN_INTERVAL_MIN:
                wait = int(MIN_INTERVAL_MIN - gap) + 1
                return False, f"距上次发布仅 {gap:.0f} 分钟，需等待 {wait} 分钟"
        return True, "ok"

    # ---------- 图片去重 ----------
    def check_image(self, image_path: str | Path) -> tuple[bool, str]:
        if self.asset_lib is None:
            return True, "ok(未挂载素材库)"
        if self.asset_lib.is_used(image_path):
            return False, f"图片已用过（hash 命中）: {Path(image_path).name}"
        return True, "ok"

    # ---------- 文案相似度 ----------
    @staticmethod
    def similarity(a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()

    def check_copy(self, text: str, pool: list[str], threshold: float = 0.60) -> tuple[bool, str]:
        """与已发布文案池比对，相似度 ≥60% 即拦截"""
        for prev in pool:
            if self.similarity(text, prev) >= threshold:
                return False, f"文案与已发布内容相似度 {self.similarity(text, prev):.0%}，需差异化"
        return True, "ok"

    # ---------- 失败率熔断 ----------
    def record_result(self, account: str, ok: bool, note: str = ""):
        """记录一次发布结果；失败率超阈值或收到验证码/违规 → 熔断"""
        acc = self.state["accounts"].setdefault(account, {})
        acc.setdefault("today_ok", 0)
        acc.setdefault("today_fail", 0)
        if ok:
            acc["today_ok"] += 1
            acc["last_date"] = dt.datetime.now().strftime("%Y-%m-%d")
            self.state["published_today"].append({
                "account": account, "time": dt.datetime.now().isoformat(), "note": note
            })
        else:
            acc["today_fail"] += 1
            total = acc["today_ok"] + acc["today_fail"]
            rate = acc["today_fail"] / total if total else 0
            if rate >= FAIL_RATE_LIMIT:
                self.suspend(account, f"今日失败率 {rate:.0%}")
            if "验证码" in note or "违规" in note or "风控" in note:
                self.suspend(account, note)
        self._save()

    def suspend(self, account: str, reason: str, hours: int = COOLDOWN_HOURS):
        until = dt.datetime.now() + dt.timedelta(hours=hours)
        self.state["suspensions"][account] = {
            "reason": reason, "until": until.isoformat()
        }
        self._save()

    # ---------- 每日归档 ----------
    def roll_day(self):
        """跨天清零：daily 指标重置，published_today 归档到日志"""
        self.state["published_today"] = []
        for acc in self.state["accounts"].values():
            acc.pop("today_ok", None)
            acc.pop("today_fail", None)
        self._save()


if __name__ == "__main__":
    rc = RiskControl(state_path="output/logs/state.json")
    now = dt.datetime(2026, 10, 27, 10, 30)
    print("频率校验:", rc.check_frequency("account_01", now))
    print("间隔校验:", rc.check_interval("account_01", now))
    print("相似度校验:", rc.check_copy("A文案", ["B文案", "A文案一模一样"]))
    rc.record_result("account_01", False, "触发验证码，请人工处理")
    print("熔断状态:", rc.check_suspension("account_01", dt.datetime.now() + dt.timedelta(minutes=1)))
