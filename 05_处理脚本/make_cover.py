# -*- coding: utf-8 -*-
"""用店家真实素材拼第一张四宫格封面（1080x1440 3:4）。"""
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Desktop\江陈记茶业\jcs_auto")
sys.path.insert(0, str(ROOT / "src"))
from image_pipeline import compose

RAW = Path(r"C:\Users\Lenovo\Downloads\jcs_raw")
OUT = ROOT / "output" / "demo"

cover = compose(
    [str(RAW / "zha_00.jpg"), str(RAW / "zha_03.jpg"), str(RAW / "zha_11.jpg"), str(RAW / "zha_13.jpg")],
    "four_grid",
    labels=["恩施玉露", "玉露利川红", "天青雅集", "楚汉茶礼"],
    title="被问爆的武汉特产！恩施玉露茶礼盒太绝了",
    out_dir=OUT,
    out_name="jcs_real_cover_1.jpg",
)
print("封面已生成:", cover)
