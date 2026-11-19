# -*- coding: utf-8 -*-
"""
make_cover5.py — 复刻江陈记日常帖拼图封面（非置顶主力款）
实帖规律（7赞日常帖「江城限定茶礼」）：2×2 四宫格实拍（花丛绿植背景、手持/开盒特写）
+ 中上部两行固定大字「武汉特色宝藏伴手礼 / 送礼首选！」
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

SRC = Path(r"C:\Users\Lenovo\Desktop\江陈记茶业\03_素材\高清素材28张")
OUT = Path(r"C:\Users\Lenovo\Desktop\江陈记茶业\04_封面成品")
FONT_B = r"C:\Windows\Fonts\msyhbd.ttc"

def fit_crop(img, w, h):
    tw, th = w, h
    iw, ih = img.size
    r = max(tw / iw, th / ih)
    img = img.resize((int(iw * r) + 1, int(ih * r) + 1), Image.LANCZOS)
    nw, nh = img.size
    x0, y0 = (nw - tw) // 2, (nh - th) // 2
    return img.crop((x0, y0, x0 + tw, y0 + th))

def make_daily_4grid(names: list[str], line1: str, line2: str, out_name: str,
                     gap: int = 6, fill="#ffffff", stroke="#1a1a1a"):
    CELL_W, CELL_H = 540, 720
    canvas = Image.new("RGB", (1080, 1440), "#ffffff")
    cells = [fit_crop(Image.open(SRC / n).convert("RGB"), CELL_W, CELL_H) for n in names]
    pos = [(0, 0), (CELL_W + gap, 0), (0, CELL_H + gap), (CELL_W + gap, CELL_H + gap)]
    for c, (x, y) in zip(cells, pos):
        canvas.paste(c, (x, y))
    # 中上部半透明底（实帖大字区 y≈430-700/1440）
    ov = Image.new("RGBA", (1080, 1440), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.rectangle([210, 480, 870, 720], fill=(0, 0, 0, 85))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), ov).convert("RGB")
    draw = ImageDraw.Draw(canvas)
    # 两行大字（偏上，实帖 y337-481/1000 → 1440 下 y485-693）
    f1 = ImageFont.truetype(FONT_B, 120)   # 武汉特色宝藏伴手礼
    f2 = ImageFont.truetype(FONT_B, 150)   # 送礼首选！
    draw.text((540, 555), line1, font=f1, fill=fill, anchor="mm", stroke_width=7, stroke_fill=stroke)
    draw.text((540, 690), line2, font=f2, fill=fill, anchor="mm", stroke_width=7, stroke_fill=stroke)
    canvas.save(OUT / out_name, "JPEG", quality=95)
    print("生成:", OUT / out_name, canvas.size)

if __name__ == "__main__":
    # 日常主力款：同款恩施玉露四宫格 + 固定大字（对标 7赞「江城限定茶礼」）
    make_daily_4grid(["zha_00.jpg", "zha_03.jpg", "zha_04.jpg", "zha_05.jpg"],
                     "武汉特色宝藏伴手礼", "送礼首选！", "jcs_cover_v5_daily_4grid.jpg")
    # 变化款：全品类四宫格 + 「武汉限定」
    make_daily_4grid(["zha_00.jpg", "zha_07.jpg", "zha_13.jpg", "zha_26.jpg"],
                     "武汉限定茶礼", "送人体面！", "jcs_cover_v5_daily_4grid_b.jpg")
