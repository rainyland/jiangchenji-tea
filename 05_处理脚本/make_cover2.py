# -*- coding: utf-8 -*-
"""按小红书爆款模板重拼：四宫格（场景标签、无横幅）+ 九宫格（中心茶礼定制大字）"""
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Desktop\江陈记茶业\jcs_auto")
sys.path.insert(0, str(ROOT / "src"))
from image_pipeline import compose

RAW = Path(r"C:\Users\Lenovo\Downloads\jcs_raw")
OUT = ROOT / "output" / "demo"

# ---- 版1：四宫格 纯四格 + 场景标签（对齐 jcs_cover_top）----
cover4 = compose(
    [str(RAW / "zha_00.jpg"), str(RAW / "zha_03.jpg"), str(RAW / "zha_11.jpg"), str(RAW / "zha_13.jpg")],
    "four_grid",
    labels=["节日茶礼", "企业团购", "烟酒批发", "旅游特产"],
    title=None,  # 爆款四宫格无顶部标题
    out_dir=OUT,
    out_name="jcs_real_cover_v2_4grid.jpg",
)
print("四宫格v2:", cover4)

# ---- 版2：九宫格 中心「茶礼定制」大字（对齐 jcs_cover2）----
nine = ["zha_00.jpg", "zha_02.jpg", "zha_03.jpg", "zha_04.jpg", "zha_07.jpg",
        "zha_09.jpg", "zha_11.jpg", "zha_13.jpg", "zha_15.jpg"]
cover9 = compose(
    [str(RAW / n) for n in nine],
    "nine_grid",
    center_text="茶礼定制",
    out_dir=OUT,
    out_name="jcs_real_cover_v2_9grid.jpg",
)
print("九宫格v2:", cover9)
