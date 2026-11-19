# -*- coding: utf-8 -*-
"""copy_engine 单元测试：标题/正文/敏感词/差异化"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from copy_engine import CopyEngine


class TestCopyEngine(unittest.TestCase):
    def setUp(self):
        self.eng = CopyEngine()

    def test_headline_formats(self):
        # 所有场景公式：必须完成占位符替换（无残留 {}），且含场景词或利益词
        for sc in ["送礼", "企业", "旅游", "门店"]:
            for seed in range(5):
                h = self.eng.make_headline(sc, "恩施玉露茶礼盒", seed=seed)
                self.assertNotIn("{", h, f"占位符未替换: {h} (scenario={sc})")
                self.assertGreater(len(h), 4)

    def test_body_has_sections(self):
        body, tags = self.eng.make_body(
            scenario="送礼", product="恩施玉露茶礼盒",
            points=["a", "b", "c"], use_scene="场景", seed=7)
        for marker in ["江陈记茶业", "评论区扣", "📍"]:
            self.assertIn(marker, body)

    def test_banned_filter(self):
        cleaned, hits = self.eng.filter_banned("这是全网最顶级的茶叶，包治百病")
        self.assertIn("**", cleaned)
        self.assertGreaterEqual(len(hits), 2)

    def test_same_seed_reproducible(self):
        a, _ = self.eng.make_body(scenario="旅游", product="利川红", points=["1", "2", "3"],
                                  use_scene="x", seed=42)
        b, _ = self.eng.make_body(scenario="旅游", product="利川红", points=["1", "2", "3"],
                                  use_scene="x", seed=42)
        self.assertEqual(a, b)

    def test_different_seed_differs(self):
        a, _ = self.eng.make_body(scenario="旅游", product="利川红", points=["1", "2", "3"],
                                  use_scene="x", seed=1)
        b, _ = self.eng.make_body(scenario="旅游", product="利川红", points=["1", "2", "3"],
                                  use_scene="x", seed=2)
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()
