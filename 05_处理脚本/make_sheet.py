# -*- coding: utf-8 -*-
"""把下载的素材拼成总览联系表（contact sheet），方便一次性查看所有素材。"""
from PIL import Image, ImageDraw
from pathlib import Path

SRC = Path(r"C:\Users\Lenovo\Downloads\jcs_raw")
OUT = Path(r"C:\Users\Lenovo\Downloads\jcs_raw\contact_sheet.jpg")

files = sorted(SRC.glob("zha_*.jpg"))
files = [f for f in files if f.name != "contact_sheet.jpg"]
print("素材数:", len(files))

THUMB_W, THUMB_H = 300, 400
COLS = 5
ROWS = (len(files) + COLS - 1) // COLS
PAD = 10
label_h = 30

sheet = Image.new("RGB", (COLS * THUMB_W + (COLS + 1) * PAD, ROWS * (THUMB_H + label_h) + (ROWS + 1) * PAD), "#222222")
draw = ImageDraw.Draw(sheet)

for i, f in enumerate(files):
    r, c = divmod(i, COLS)
    x = PAD + c * (THUMB_W + PAD)
    y = PAD + r * (THUMB_H + label_h + PAD)
    img = Image.open(f).convert("RGB")
    img.thumbnail((THUMB_W, THUMB_H), Image.LANCZOS)
    sheet.paste(img, (x, y))
    draw.rectangle([x, y + THUMB_H, x + THUMB_W, y + THUMB_H + label_h], fill="#111111")
    draw.text((x + 6, y + THUMB_H + 6), f.name, fill="#ffffff")

sheet.save(OUT, "JPEG", quality=85)
print("总览图:", OUT, sheet.size)
