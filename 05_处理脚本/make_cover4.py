# -*- coding: utf-8 -*-
"""
make_cover4.py — 复刻江陈记实帖四宫格拼图封面
实帖规律（163赞置顶）：2×2 实拍拼接（手持礼盒+自然背景）+ 中部两行大字「湖北 / 特色茶叶伴手礼」
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

SRC = Path(r"C:\Users\Lenovo\Desktop\江陈记茶业\03_素材\高清素材28张")
OUT = Path(r"C:\Users\Lenovo\Desktop\江陈记茶业\04_封面成品")
FONT_B = r"C:\Windows\Fonts\msyhbd.ttc"

def fit_crop(img, w, h):
    """按目标比例居中裁剪缩放"""
    tw, th = w, h
    iw, ih = img.size
    r = max(tw / iw, th / ih)
    img = img.resize((int(iw * r) + 1, int(ih * r) + 1), Image.LANCZOS)
    nw, nh = img.size
    x0, y0 = (nw - tw) // 2, (nh - th) // 2
    return img.crop((x0, y0, x0 + tw, y0 + th))

def make_4grid(names: list[str], main1: str, main2: str, out_name: str,
               gap: int = 8, title_fill="#ffffff", stroke="#1a1a1a"):
    CELL_W, CELL_H = 540, 720      # 2×2 → 1080×1440
    canvas = Image.new("RGB", (1080, 1440), "#ffffff")
    cells = [fit_crop(Image.open(SRC / n).convert("RGB"), CELL_W, CELL_H) for n in names]
    pos = [(0, 0), (CELL_W + gap, 0), (0, CELL_H + gap), (CELL_W + gap, CELL_H + gap)]
    for c, (x, y) in zip(cells, pos):
        canvas.paste(c, (x, y))
    draw = ImageDraw.Draw(canvas)
    # 中部两行大字（实帖位置：画面中心偏下）
    f1 = ImageFont.truetype(FONT_B, 130)
    f2 = ImageFont.truetype(FONT_B, 160)
    cy1 = 690 + 70
    cy2 = 690 + 70 + 150 + 20
    draw.text((540, cy1), main1, font=f1, fill=title_fill, anchor="mm",
              stroke_width=8, stroke_fill=stroke)
    draw.text((540, cy2), main2, font=f2, fill=title_fill, anchor="mm",
              stroke_width=8, stroke_fill=stroke)
    # 轻微半透明底提升可读性
    ov = Image.new("RGBA", (1080, 1440), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.rectangle([240, 620, 840, 980], fill=(0, 0, 0, 90))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), ov).convert("RGB")
    draw = ImageDraw.Draw(canvas)
    draw.text((540, cy1), main1, font=f1, fill=title_fill, anchor="mm",
              stroke_width=8, stroke_fill=stroke)
    draw.text((540, cy2), main2, font=f2, fill=title_fill, anchor="mm",
              stroke_width=8, stroke_fill=stroke)
    canvas.save(OUT / out_name, "JPEG", quality=95)
    print("生成:", OUT / out_name, canvas.size)

if __name__ == "__main__":
    # 复刻版 A：同款恩施玉露四宫格（贴近实帖 163赞 封面）
    make_4grid(["zha_00.jpg", "zha_03.jpg", "zha_04.jpg", "zha_05.jpg"],
               "湖北", "特色茶叶伴手礼", "jcs_cover_v4_4grid_a.jpg")
    # 复刻版 B：全品类混拼（恩施玉露+利川红+楚汉茶礼）
    make_4grid(["zha_00.jpg", "zha_07.jpg", "zha_13.jpg", "zha_26.jpg"],
               "湖北", "特色茶叶伴手礼", "jcs_cover_v4_4grid_b.jpg")
