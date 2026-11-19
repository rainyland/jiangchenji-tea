# -*- coding: utf-8 -*-
"""image_pipeline 单元测试：模板可用性 + 输出尺寸"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from PIL import Image

from image_pipeline import compose, single_text, four_grid, nine_grid


class TestImagePipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.demo = []
        for i, color in enumerate([(180, 30, 30), (20, 110, 60), (200, 150, 40), (60, 80, 160)]):
            p = cls.tmp / f"d{i}.jpg"
            Image.new("RGB", (800, 800), color).save(p, "JPEG")
            cls.demo.append(str(p))
        cls.out = cls.tmp / "out"

    def test_four_grid(self):
        out = compose(self.demo, "four_grid", labels=["A", "B", "C", "D"],
                      title="测试标题", out_dir=self.out, out_name="fg.jpg")
        img = Image.open(out)
        self.assertEqual(img.size, (1080, 1440))

    def test_nine_grid(self):
        out = compose(self.demo, "nine_grid", center_text="茶礼定制",
                      corner_labels=["a", "b", "c", "d"], out_dir=self.out, out_name="ng.jpg")
        self.assertEqual(Image.open(out).size, (1080, 1440))

    def test_single(self):
        out = compose(self.demo, "single_text", headline="全品类价目表", title="副标题",
                      out_dir=self.out, out_name="sg.jpg")
        self.assertEqual(Image.open(out).size, (1080, 1440))

    def test_template_missing_raises(self):
        with self.assertRaises(ValueError):
            compose(self.demo, "no_such", out_dir=self.out)


if __name__ == "__main__":
    unittest.main()
