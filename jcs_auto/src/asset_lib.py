# -*- coding: utf-8 -*-
"""
asset_lib.py — 素材库管理
职责：
  1. 初始化树状素材目录（产品线/场景/文字素材/成图输出/已用图）
  2. 扫描素材并生成图片指纹（hash），供发布去重
  3. 已用图登记：发布成功的图写入 05_已用图 索引，禁止重复使用
"""
import hashlib
import json
import os
from pathlib import Path

# 树状目录规范（相对 assets 根）
TREE = {
    "01_产品线": ["恩施玉露", "利川红", "茶礼盒", "企业定制"],
    "02_场景": ["送礼", "旅游", "企业团购", "门店"],
    "03_文字素材": [],
    "04_成图输出": [],
    "05_已用图": [],
}

INDEX_FILE = "used_index.json"   # 已用图索引文件（放 assets 根）
HASH_FILE = "asset_hashes.json"  # 素材指纹缓存（放 assets 根）


class AssetLibrary:
    def __init__(self, assets_root: str):
        self.root = Path(assets_root)
        self.index_path = self.root / INDEX_FILE
        self.hash_path = self.root / HASH_FILE
        self._ensure_tree()

    # ---------- 目录 ----------
    def _ensure_tree(self):
        """确保树状目录存在（首次运行时创建）"""
        for top, subs in TREE.items():
            d = self.root / top
            d.mkdir(parents=True, exist_ok=True)
            for sub in subs:
                (d / sub).mkdir(parents=True, exist_ok=True)

    # ---------- 图片指纹 ----------
    @staticmethod
    def image_hash(path: str | Path, chunk: int = 65536) -> str:
        """对图片文件算 SHA-256 指纹（分块读，省内存）"""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                data = f.read(chunk)
                if not data:
                    break
                h.update(data)
        return h.hexdigest()

    def scan_assets(self) -> list[dict]:
        """扫描 01_产品线 / 02_场景 下的所有图片，返回 [{path, hash, cat, sub}]"""
        found = []
        for top in ("01_产品线", "02_场景"):
            base = self.root / top
            if not base.exists():
                continue
            for p in base.rglob("*"):
                if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
                    found.append({
                        "path": str(p),
                        "hash": self.image_hash(p),
                        "cat": top,
                        "sub": p.parent.name,          # 子目录 = 系列名（恩施玉露/利川红/楚汉茶礼…）
                    })
        # 缓存指纹
        self._write_json(self.hash_path, found)
        return found

    def load_hashes(self) -> list[dict]:
        if self.hash_path.exists():
            return self._read_json(self.hash_path) or []
        return []

    # ---------- 已用图登记 / 去重 ----------
    def _load_used(self) -> dict:
        if self.index_path.exists():
            data = self._read_json(self.index_path)
            if data:
                return data
        return {"records": [], "hashes": {}}

    def mark_used(self, image_path: str | Path, note: str = ""):
        """登记一张已发布的图（含生成图），防止重复使用"""
        p = Path(image_path)
        img_hash = self.image_hash(p)
        used = self._load_used()
        rec = {
            "path": str(p),
            "hash": img_hash,
            "note": note,
        }
        used["records"].append(rec)
        used["hashes"][img_hash] = str(p)
        self._write_json(self.index_path, used)
        return img_hash

    def is_used(self, image_path: str | Path) -> bool:
        """判断图片是否已用过（指纹命中）"""
        try:
            img_hash = self.image_hash(image_path)
        except OSError:
            return False
        used = self._load_used()
        return img_hash in used.get("hashes", {})

    def pick_unused(self, candidates: list[dict], limit: int = 6,
                    exclude: set[str] | None = None) -> list[dict]:
        """从候选素材里挑未用过的图（支持按产品线/场景过滤）

        exclude: 本批队列已占用图的 hash 集合（可选）。
        传入后同一批不同账号选到的图互不重复，防止同一天发同一张图。
        """
        used = self._load_used().get("hashes", {})
        exclude = exclude or set()
        picked = []
        for c in candidates:
            if c["hash"] not in used and c["hash"] not in exclude:
                picked.append(c)
            if len(picked) >= limit:
                break
        return picked

    # ---------- 工具 ----------
    @staticmethod
    def _write_json(path: Path, data):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _read_json(path: Path):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None


if __name__ == "__main__":
    lib = AssetLibrary(os.path.join(os.path.dirname(__file__), "..", "assets"))
    print("素材指纹扫描：", len(lib.scan_assets()), "张")
    print("已用图索引：", lib._load_used()["hashes"])
