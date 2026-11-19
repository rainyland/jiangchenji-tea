# -*- coding: utf-8 -*-
"""下载小红书笔记封面 + 拼总览图，供逐条拆解。"""
import json, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw

SRC = Path(r"C:\Users\Lenovo\Downloads\xhs_notes.json")
OUT = Path(r"C:\Users\Lenovo\Downloads\xhs_covers")
OUT.mkdir(parents=True, exist_ok=True)

notes = json.loads(SRC.read_text(encoding="utf-8"))
print("笔记数:", len(notes))

ok = []
for i, n in enumerate(notes):
    url = n["img"]
    if not url:
        continue
    dest = OUT / f"note_{i:02d}.jpg"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
            f.write(r.read())
        ok.append((i, dest))
    except Exception as e:
        print(f"FAIL {i}: {e}")

print(f"下载成功 {len(ok)}/{len(notes)}")

# 拼总览图（5 列，每格标注序号+赞数）
files = [OUT / f"note_{i:02d}.jpg" for i, _ in ok]
TW, TH = 270, 360
COLS = 5
ROWS = (len(files) + COLS - 1) // COLS
PAD = 8
LH = 44
sheet = Image.new("RGB", (COLS * TW + (COLS + 1) * PAD, ROWS * (TH + LH) + (ROWS + 1) * PAD), "#1a1a1a")
draw = ImageDraw.Draw(sheet)
for idx, f in enumerate(files):
    r, c = divmod(idx, COLS)
    x = PAD + c * (TW + PAD)
    y = PAD + r * (TH + LH + PAD)
    try:
        img = Image.open(f).convert("RGB")
        img.thumbnail((TW, TH), Image.LANCZOS)
        sheet.paste(img, (x, y))
    except Exception as e:
        draw.rectangle([x, y, x + TW, y + TH], fill="#333")
    like = notes[idx]["like"]
    title = notes[idx]["t"][:14]
    draw.rectangle([x, y + TH, x + TW, y + TH + LH], fill="#0d0d0d")
    draw.text((x + 6, y + TH + 6), f"{idx:02d} ♥{like} {title}", fill="#ffffff")

sheet.save(OUT / "all_covers.jpg", "JPEG", quality=85)
print("总览:", OUT / "all_covers.jpg", sheet.size)
