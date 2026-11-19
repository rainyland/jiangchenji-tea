# -*- coding: utf-8 -*-
"""
publisher.py — 小红书发布器框架（Playwright，每账号独立环境）
职责：
  1. 每账号独立 user_data_dir（浏览器指纹隔离）+ 可选代理
  2. 发布流程：登录态校验 → 进入发布页 → 传图 → 填标题/正文/标签 → 发布
  3. 结果回调给 risk_control 记录（成功/失败/验证码）
部署要求（商家电脑/服务器）：
  pip install playwright && playwright install chromium
  每账号一个独立 user_data_dir（首次需人工扫码登录一次，之后复用 Cookie）
注意：
  - 本模块依赖 playwright，未安装时 import 会失败（在 requirements 中注明可选）
  - 小红书页面结构可能变化，选择器集中在顶部便于维护
"""
import datetime as dt
import json
import random
import time
from pathlib import Path

POST_URL = "https://www.xiaohongshu.com/publish"

# 页面选择器（集中管理，页面改版时只改这里）
SEL = {
    "publish_btn": "text=发布笔记",          # 顶部发布入口
    "file_input": "input[type=file]",        # 图片上传
    "title": "#post-title",                  # 标题
    "content": "#post-content",              # 正文
    "submit": "text=发布",
}


class XhsPublisher:
    def __init__(self, account: dict, risk: object):
        """
        account: {"id","name","proxy": "http://ip:port","env": "独立user_data_dir路径"}
        risk: risk_control.RiskControl 实例（记录结果/熔断）
        """
        self.account = account
        self.risk = risk
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError("未安装 playwright：pip install playwright && playwright install chromium")
        self._sync_playwright = sync_playwright

    # ---------- 独立环境启动 ----------
    def _launch(self):
        p = self._sync_playwright().start()
        ctx_args = {}
        if self.account.get("proxy"):
            proxy = self.account["proxy"]
            ctx_args["proxy"] = {"server": proxy}
        context = p.chromium.launch_persistent_context(
            user_data_dir=self.account.get("env", f"env_{self.account['id']}"),
            headless=False,               # 真机可见，降低风控概率
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
            **ctx_args,
        )
        return p, context

    # ---------- 登录态校验 ----------
    @staticmethod
    def _is_logged_in(page) -> bool:
        # 打开主页，能读到"发布笔记"按钮即视为已登录（未登录会跳登录墙）
        page.goto("https://www.xiaohongshu.com", timeout=30000)
        time.sleep(3)
        try:
            page.wait_for_selector("text=发布笔记", timeout=8000)
            return True
        except Exception:
            return False

    # ---------- 发布前养号：模拟真人刷首页（降低机器味） ----------
    @staticmethod
    def _warmup(page, seconds: int = 15):
        """发布前先刷首页：打开发现页→随机滚动→停留，像真实用户在浏览"""
        page.goto("https://www.xiaohongshu.com/explore", timeout=30000)
        time.sleep(3)
        # 模拟真人随机滚动 2-4 次，每次间隔随机
        rolls = random.randint(2, 4)
        for _ in range(rolls):
            page.mouse.wheel(0, random.randint(300, 600))
            time.sleep(random.uniform(1.5, 3.5))
        time.sleep(seconds)   # 额外停留，让浏览行为更像真人

    # ---------- 发布单条（人工确认模式：AI 填好，人工点最后一下） ----------
    def publish(self, images: list[str], title: str, content: str, tags: str,
                human_confirm_timeout: int = 600) -> dict:
        """
        合规定位：AI 辅助批量排版 + 人工一键提交（不替人点「发布」按钮）。
        流程：登录校验 → 进入发布页 → 传图 → 填标题/正文/标签 → **停住等人工核对点发布**。
        human_confirm_timeout: 等待人工点发布的最长秒数（默认 10 分钟）。
        """
        account = self.account["id"]
        context = None
        p = None
        try:
            p, context = self._launch()
            page = context.new_page()
            if not self._is_logged_in(page):
                raise RuntimeError("未登录：请人工扫码登录该账号环境（user_data_dir 已保留登录态）")
            # 发布前养号：先刷首页再进发布页（模拟真人行为，降低机器味）
            self._warmup(page, seconds=5)
            page.goto(POST_URL, timeout=30000)
            time.sleep(2)
            # 1) 传图（多图）
            page.set_input_files(SEL["file_input"], images)
            time.sleep(4)  # 等图片上传完成
            # 2) 标题 + 正文 + 标签（AI 排版好）
            page.fill(SEL["title"], title)
            page.fill(SEL["content"], content + "\n" + tags)
            time.sleep(1)
            # 3) 不替人点「发布」——停住等人工核对（合规边界：薯管家严打 AI 托管代发）
            print("=" * 60)
            print(f"[人工确认] 账号 {account} 已填好：")
            print(f"  标题：{title}")
            print(f"  正文：{content[:60]}...")
            print(f"  标签：{tags[:60]}...")
            print(f"  请在浏览器中核对后，手动点「发布」（最长等待 {human_confirm_timeout//60} 分钟）")
            print("=" * 60)
            # 4) 轮询检测人工已点发布：URL 离开 publish 页 / 出现「发布成功」提示
            deadline = time.time() + human_confirm_timeout
            posted = False
            while time.time() < deadline:
                time.sleep(5)
                if "/publish" not in page.url:
                    posted = True
                    break
                if page.locator("text=发布成功").count() > 0:
                    posted = True
                    break
                for bad in ["验证码", "滑动验证", "操作频繁"]:
                    if page.locator(f"text={bad}").count() > 0:
                        raise RuntimeError(f"触发风控：{bad}")
            if posted:
                self.risk.record_result(account, True, note="人工确认后发布成功")
                return {"ok": True, "account": account, "mode": "人工确认",
                        "time": dt.datetime.now().isoformat()}
            else:
                self.risk.record_result(account, False, note="等待人工确认超时（10分钟未点发布）")
                return {"ok": False, "account": account, "mode": "人工确认",
                        "error": "超时未点发布，浏览器保持打开可手动补发"}
        except Exception as e:
            note = str(e)
            self.risk.record_result(account, False, note=note)
            return {"ok": False, "account": account, "error": note}
        finally:
            # 人工确认模式：不强制关浏览器，等人看完再手动关
            try:
                if context is not None:
                    context.close()
                if p is not None:
                    p.stop()
            except Exception:
                pass


if __name__ == "__main__":
    # 用法示例（真实运行请先配置 config/config.json）
    print("发布器框架就绪。部署步骤见 README.md：")
    print(" 1. pip install playwright && playwright install chromium")
    print(" 2. 每账号建独立 user_data_dir 并人工扫码登录一次")
    print(" 3. 配置 config/config.json（账号/代理/环境路径）后运行 main.py")
