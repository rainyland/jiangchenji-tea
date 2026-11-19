# -*- coding: utf-8 -*-
"""从 xhs_notes.json 重新下载 30 张小红书封面（恢复误删）。"""
import json, urllib.request
from pathlib import Path

SRC = Path(r"C:\Users\Lenovo\Desktop\江陈记茶业\03_素材\小红书封面30张\xhs_notes.json")
DEST = Path(r"C:\Users\Lenovo\Desktop\江陈记茶业\03_素材\小红书封面30张")
DEST.mkdir(parents=True, exist_ok=True)

notes = json.loads(SRC.read_text(encoding="utf-8"))
ok, fail = 0, 0
for i, n in enumerate(notes):
    url = n["img"]
    dest = DEST / f"note_{i:02d}.jpg"
    if dest.exists() and dest.stat().st_size > 5000:
        ok += 1
        continue
    if not url:
        fail += 1
        continue
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
            f.write(r.read())
        ok += 1
    except Exception as e:
        fail += 1
        print(f"FAIL {i}: {e}")
print(f"恢复成功 {ok} / 失败 {fail}")
