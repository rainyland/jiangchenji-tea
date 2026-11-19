# -*- coding: utf-8 -*-
"""
make_cover6.py — 按系列复刻日常拼图（对标实帖字号与版式）
实帖规律（7赞日常帖）：
  ① 同款产品多角度 = 一个系列 4 格（手提袋/合盖/开盖/托举）
  ② 大字字号约 60-70px（1080×1440），白字细描边，中上部两行，无大黑底
  ③ 行距紧凑
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

SRC = Path(r"C:\Users\Lenovo\Desktop\江陈记茶业\03_素材\高清素材28张")
OUT = Path(r"C:\Users\Lenovo\Desktop\江陈记茶业\04_封面成品")
FONT_B = r"C:\Windows\Fonts\simhei.ttf"  # 黑体，更粗更方，贴近POP海报风

# 系列素材（同款产品多角度）
SERIES = {
    "shuangpin": ["zha_03.jpg", "zha_04.jpg", "zha_05.jpg", "zha_06.jpg"],   # 恩施玉露·利川红双拼套装
    "lichuan":   ["zha_07.jpg", "zha_17.jpg", "zha_08.jpg", "zha_10.jpg"],   # 利川红·東湖茶叙：红袋→俯视→正面→开盖
    "chuhan":    ["zha_25.jpg", "zha_13.jpg", "zha_23.jpg", "zha_24.jpg"],   # 楚汉茶礼：袋→合盖→掀盖→开盖平放
}

def fit_crop(img, w, h):
    iw, ih = img.size
    r = max(w / iw, h / ih)
    img = img.resize((int(iw * r) + 1, int(ih * r) + 1), Image.LANCZOS)
    nw, nh = img.size
    x0, y0 = (nw - w) // 2, (nh - h) // 2
    return img.crop((x0, y0, x0 + w, y0 + h))

def make_series_cover(key: str, line1: str, line2: str, out_name: str,
                      fs1: int = 92, fs2: int = 104, gap: int = 6,
                      fill="#ffffff", stroke="#000000"):
    CELL_W, CELL_H = 540, 720
    canvas = Image.new("RGB", (1080, 1440), "#ffffff")
    for n, (x, y) in zip(SERIES[key], [(0, 0), (540 + gap, 0), (0, 720 + gap), (540 + gap, 720 + gap)]):
        canvas.paste(fit_crop(Image.open(SRC / n).convert("RGB"), CELL_W, CELL_H), (x, y))
    draw = ImageDraw.Draw(canvas)
    f1 = ImageFont.truetype(FONT_B, fs1)
    f2 = ImageFont.truetype(FONT_B, fs2)
    # 第一行：白色粗描边
    draw.text((540, 610), line1, font=f1, fill=fill, anchor="mm", stroke_width=8, stroke_fill=stroke)
    # 第二行：白色主体 + 红色感叹号
    if line2.endswith("！") or line2.endswith("!"):
        body = line2[:-1]
        # 画白色主体
        draw.text((540, 835), body, font=f2, fill=fill, anchor="mm", stroke_width=8, stroke_fill=stroke)
        # 计算主体宽度，在右侧画红色感叹号
        bbox = draw.textbbox((0, 0), body, font=f2)
        body_w = bbox[2] - bbox[0]
        ex_x = 540 + body_w // 2 + 10
        draw.text((ex_x, 835), "！", font=f2, fill="#ff2222", anchor="lm", stroke_width=8, stroke_fill=stroke)
    else:
        draw.text((540, 835), line2, font=f2, fill=fill, anchor="mm", stroke_width=8, stroke_fill=stroke)
    canvas.save(OUT / out_name, "JPEG", quality=95)
    print("生成:", OUT / out_name, canvas.size)

def make_collage_cover(images: list, line1: str, line2: str, out_name: str,
                       fs1: int = 56, fs2: int = 72):
    """错落拼贴款：4张图错落拼，金色字体，标题居中"""
    canvas = Image.new("RGB", (1080, 1440), "#2d5a3d")  # 深绿背景
    # 4张图错落位置（不是整齐四宫格）
    positions = [
        (80, 100, 380, 380),   # 左上
        (580, 80, 420, 320),   # 右上（偏上）
        (100, 500, 360, 360),  # 左下（偏下）
        (560, 460, 440, 380),  # 右下
    ]
    for n, (x, y, w, h) in zip(images, positions):
        img = fit_crop(Image.open(SRC / n).convert("RGB"), w, h)
        canvas.paste(img, (x, y))
    draw = ImageDraw.Draw(canvas)
    f1 = ImageFont.truetype(FONT_B, fs1)
    f2 = ImageFont.truetype(FONT_B, fs2)
    # 金色字体，居中，在中间位置
    gold = "#d4a84b"
    # 第一行小字
    draw.text((540, 780), line1, font=f1, fill=gold, anchor="mm")
    # 第二行大字
    draw.text((540, 870), line2, font=f2, fill=gold, anchor="mm")
    canvas.save(OUT / out_name, "JPEG", quality=95)
    print("生成拼贴:", OUT / out_name, canvas.size)


def make_note_cover(line1: str, line2: str, out_name: str,
                    fs1: int = 64, fs2: int = 76):
    """便签纸款：黄色便签背景，手写感文字"""
    canvas = Image.new("RGB", (1080, 1440), "#fff9e6")  # 淡黄便签色
    draw = ImageDraw.Draw(canvas)
    f1 = ImageFont.truetype(FONT_B, fs1)
    f2 = ImageFont.truetype(FONT_B, fs2)
    # 画个便签纸的感觉：左上角胶带
    draw.rectangle([(100, 150), (250, 180)], fill="#f0e6c0")
    # 文字居中偏上
    draw.text((540, 400), line1, font=f1, fill="#333333", anchor="mm")
    draw.text((540, 500), line2, font=f2, fill="#333333", anchor="mm")
    # 底部加几个小图装饰
    deco_imgs = ["zha_03.jpg", "zha_07.jpg", "zha_13.jpg"]
    positions = [(150, 900), (390, 950), (630, 900)]
    for n, (x, y) in zip(deco_imgs, positions):
        img = fit_crop(Image.open(SRC / n).convert("RGB"), 240, 240)
        canvas.paste(img, (x, y))
    canvas.save(OUT / out_name, "JPEG", quality=95)
    print("生成便签:", OUT / out_name, canvas.size)


if __name__ == "__main__":
    # 1. 四宫格常规款（已有的）
    make_series_cover("shuangpin", "武汉特产必带", "双拼伴手礼物", "jcs_v6_shuangpin.jpg")
    make_series_cover("lichuan",   "来武汉一定不要", "空手回去！", "jcs_v6_lichuan.jpg")
    make_series_cover("chuhan",     "在武汉必带", "十大伴手礼之一", "jcs_v6_chuhan.jpg")

    # 2. 错落拼贴款（照着他们真实风格做的）
    collage_imgs = ["zha_07.jpg", "zha_08.jpg", "zha_10.jpg", "zha_17.jpg"]
    make_collage_cover(collage_imgs, "武汉茶礼", "旅游优选特产伴手礼", "jcs_v6_collage.jpg")
