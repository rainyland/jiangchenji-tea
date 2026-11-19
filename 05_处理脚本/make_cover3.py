# -*- coding: utf-8 -*-
"""
make_cover3.py — 按店家方向（拼图+标题）生成封面：单图大字版式
主图（绿植背景产品实拍）+ 标题大字（白字黑描边）+ 副标题行
对应拆解结论：30 条封面 67% 为单图大字主力版式。
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

SRC = Path(r"C:\Users\Lenovo\Desktop\江陈记茶业\03_素材\高清素材28张")
OUT = Path(r"C:\Users\Lenovo\Desktop\江陈记茶业\04_封面成品")
FONT_B = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_R = r"C:\Windows\Fonts\msyh.ttc"

def stroke_text(draw, xy, text, font, fill="#ffffff", stroke="#1a1a1a", sw=6, anchor="mm"):
    draw.text(xy, text, font=font, fill=fill, anchor=anchor,
              stroke_width=sw, stroke_fill=stroke)

def make_cover(src_name: str, main_title: str, sub_title: str, out_name: str,
               main_fill="#ffffff", sub_fill="#ffe9a8"):
    img = Image.open(SRC / src_name).convert("RGB")
    # 裁剪为 3:4（1080x1440）
    w, h = img.size
    target = 1080 / 1440
    if w / h > target:      # 太宽，裁左右
        nw = int(h * target)
        x0 = (w - nw) // 2
        img = img.crop((x0, 0, x0 + nw, h))
    else:                   # 太高，裁上下（保中部偏下，产品通常在中心）
        nh = int(w / target)
        y0 = max(0, (h - nh) // 2)
        img = img.crop((0, y0, w, y0 + nh))
    img = img.resize((1080, 1440), Image.LANCZOS)

    # 顶部渐变遮罩（保证标题可读）+ 底部轻微渐变
    ov = Image.new("L", (1080, 1440), 0)
    d = ImageDraw.Draw(ov)
    for y in range(420):
        a = int(180 * (1 - y / 420))
        d.line([(0, y), (1080, y)], fill=a)
    for y in range(1440 - 300, 1440):
        a = int(140 * (y - (1440 - 300)) / 300)
        d.line([(0, y), (1080, y)], fill=a)
    black = Image.new("RGB", (1080, 1440), "#000000")
    img = Image.composite(black, img, ov)

    draw = ImageDraw.Draw(img)

    # 主标题大字（上1/3处）
    main_font = ImageFont.truetype(FONT_B, 150)
    stroke_text(draw, (540, 330), main_title, main_font, fill=main_fill)

    # 分隔线
    draw.line([(380, 450), (700, 450)], fill="#ffffff", width=4)

    # 副标题行
    sub_font = ImageFont.truetype(FONT_B, 52)
    stroke_text(draw, (540, 520), sub_title, sub_font, fill=sub_fill, sw=4)

    # 底部小字（品牌）
    foot_font = ImageFont.truetype(FONT_R, 40)
    stroke_text(draw, (540, 1330), "江陈记茶业 · 湖北武汉特产", foot_font, fill="#ffffff", sw=3)

    img.save(OUT / out_name, "JPEG", quality=95)
    print("生成:", OUT / out_name, img.size)

if __name__ == "__main__":
    # 示例A：送礼场景（恩施玉露主图）
    make_cover("zha_00.jpg", "武汉伴手礼", "恩施玉露茶礼盒 ｜ 走亲访友超有面儿", "jcs_cover_v3_songli.jpg")
    # 示例B：旅游场景（恩施玉露主图）
    make_cover("zha_26.jpg", "湖北特产", "恩施玉露茶礼盒 ｜ 来武汉必带·返程伴手礼", "jcs_cover_v3_lvyou.jpg")
