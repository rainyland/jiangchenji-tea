# -*- coding: utf-8 -*-
"""批量下载百度网盘分享素材高清缩略版（c1080_u1440），从已保存的 URL 列表。"""
import json, urllib.request, os, sys
from pathlib import Path

URLS_FILE = Path(r"C:\Users\Lenovo\Downloads\zha_urls.json")
OUT_DIR = Path(r"C:\Users\Lenovo\Downloads\jcs_raw")
OUT_DIR.mkdir(parents=True, exist_ok=True)

urls = json.loads(URLS_FILE.read_text(encoding="utf-8"))
print(f"URL 总数: {len(urls)}")

ok, fail = 0, 0
for i, u in enumerate(urls):
    u2 = u.replace("size=c180_u194", "size=c1080_u1440")
    dest = OUT_DIR / f"zha_{i:02d}.jpg"
    if dest.exists() and dest.stat().st_size > 10000:
        ok += 1
        continue
    try:
        req = urllib.request.Request(u2, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
            f.write(r.read())
        ok += 1
    except Exception as e:
        fail += 1
        print(f"  FAIL {i}: {e}")
print(f"成功 {ok} / 失败 {fail}")
