# -*- coding: utf-8 -*-
"""
image_pipeline.py — 拼图配字引擎（对齐江陈记爆款封面风格）
职责：
  1. 模板：四宫格场景图 / 九宫格产品矩阵 / 单图+大字利益点
  2. 图片 cover 裁切对齐、拼接、加标签条
  3. 中文大字渲染（黑体/雅黑 + 描边 + 阴影），文字位置按模板固定
  4. 导出 3:4 竖图 1080x1440，JPG 质量 85
"""
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CANVAS_W, CANVAS_H = 1080, 1440  # 3:4 竖图

# ---------- 字体探测 ----------
_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyhbd.ttc",   # 微软雅黑 Bold
    r"C:\Windows\Fonts\msyh.ttc",     # 微软雅黑
    r"C:\Windows\Fonts\simhei.ttf",   # 黑体
    r"C:\Windows\Fonts\simsun.ttc",   # 宋体
    "/System/Library/Fonts/PingFang.ttc",   # macOS
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux 文泉驿
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """加载中文字体，找不到就抛错（部署时确保系统有黑体/雅黑）"""
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    raise RuntimeError("未找到中文字体，请安装微软雅黑或黑体（msyh.ttc / simhei.ttf）")


def _cover(img: Image.Image, w: int, h: int) -> Image.Image:
    """cover 裁切：按目标比例居中裁切并缩放，不留黑边"""
    iw, ih = img.size
    target = w / h
    src = iw / ih
    if src > target:  # 太宽：裁左右
        nw = int(ih * target)
        x0 = (iw - nw) // 2
        img = img.crop((x0, 0, x0 + nw, ih))
    else:            # 太高：裁上下
        nh = int(iw / target)
        y0 = (ih - nh) // 2
        img = img.crop((0, y0, iw, y0 + nh))
    return img.resize((w, h), Image.LANCZOS)


def _draw_text(draw: ImageDraw.ImageDraw, xy, text, font, fill,
               stroke_fill="#000000", stroke_width=0, anchor="mm", shadow=True):
    """画文字（可选阴影+描边），xy 为锚点中心坐标"""
    if shadow and stroke_width > 0:
        draw.text((xy[0] + 4, xy[1] + 4), text, font=font, fill="#00000066", anchor=anchor)
    draw.text(xy, text, font=font, fill=fill, anchor=anchor,
              stroke_width=stroke_width, stroke_fill=stroke_fill)


def _wrap_text(text: str, max_chars: int) -> list[str]:
    """按最大字符数换行（中文按字数）"""
    if len(text) <= max_chars:
        return [text]
    lines = []
    while len(text) > max_chars:
        lines.append(text[:max_chars])
        text = text[max_chars:]
    lines.append(text)
    return lines


# ---------- 模板 1：四宫格场景图 ----------
def four_grid(images: list[Image.Image], labels: list[str],
              title: str | None = None) -> Image.Image:
    """
    2x2 四宫格 + 每格底部标签条；可选顶部标题条。
    images: 恰好 4 张；labels: 恰好 4 个场景词（节日茶礼/企业团购/烟酒批发/旅游特产）
    """
    assert len(images) == 4 and len(labels) == 4, "四宫格需要 4 张图 + 4 个标签"
    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), "#ffffff")
    draw = ImageDraw.Draw(canvas)

    pad = 10                    # 格间距
    title_h = 0
    if title:
        title_h = 140

    cell_w = (CANVAS_W - 3 * pad) // 2
    usable_h = CANVAS_H - title_h
    cell_h_img = (usable_h - 3 * pad) // 2 - 70   # 每格留 70 给标签条
    tag_h = 60

    pos = [(0, 0), (1, 0), (0, 1), (1, 1)]
    for i, (img, label) in enumerate(zip(images, labels)):
        gx, gy = pos[i]
        x = pad + gx * (cell_w + pad)
        y = title_h + pad + gy * (cell_h_img + tag_h + pad)
        cell = _cover(img, cell_w, cell_h_img)
        canvas.paste(cell, (x, y))
        # 标签条：半透明黑底 + 白字
        bar = Image.new("RGBA", (cell_w, tag_h), (0, 0, 0, 150))
        canvas.paste(bar, (x, y + cell_h_img))
        f_tag = _load_font(34)
        _draw_text(draw, (x + cell_w / 2, y + cell_h_img + tag_h / 2), label,
                   f_tag, "#ffffff", stroke_fill="#000000", stroke_width=2)

    if title:
        f_title = _load_font(60)
        _draw_text(draw, (CANVAS_W / 2, title_h / 2 + 10), title,
                   f_title, "#ffffff", stroke_fill="#8B0000", stroke_width=4,
                   shadow=True)
        top_bar = Image.new("RGBA", (CANVAS_W, title_h), (139, 0, 0, 235))
        canvas.paste(top_bar, (0, 0))
        # 深红底上重画标题
        draw = ImageDraw.Draw(canvas)
        _draw_text(draw, (CANVAS_W / 2, title_h / 2 + 10), title,
                   f_title, "#ffffff", stroke_fill="#5a0000", stroke_width=4)
    return canvas


# ---------- 模板 2：九宫格产品矩阵 ----------
def nine_grid(images: list[Image.Image], center_text: str,
              corner_labels: list[str] | None = None) -> Image.Image:
    """
    3x3 产品矩阵，中心格覆盖大字（如「茶礼定制」）。
    images: 1~9 张（缺格用白底）；center_text: 中心大字；corner_labels: 四角小标
    """
    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), "#f5f0e8")
    draw = ImageDraw.Draw(canvas)

    pad = 8
    cell_w = (CANVAS_W - 4 * pad) // 3
    cell_h = cell_w
    start_y = (CANVAS_H - 3 * cell_h - 4 * pad) // 2   # 垂直居中

    slots = list(range(9))
    for i in slots:
        r, c = divmod(i, 3)
        x = pad + c * (cell_w + pad)
        y = start_y + pad + r * (cell_h + pad)
        if i < len(images):
            cell = _cover(images[i], cell_w, cell_h)
            canvas.paste(cell, (x, y))
        else:
            draw.rectangle([x, y, x + cell_w, y + cell_h], fill="#e8e0d0")

    # 中心格覆盖大字（半透明深红底 + 艺术字）
    cx = pad + 1 * (cell_w + pad)
    cy = start_y + pad + 1 * (cell_h + pad)
    overlay = Image.new("RGBA", (cell_w, cell_h), (139, 0, 0, 200))
    canvas.paste(overlay, (cx, cy))
    draw = ImageDraw.Draw(canvas)
    f_center = _load_font(72)
    for ln, line in enumerate(_wrap_text(center_text, 4)):
        _draw_text(draw, (cx + cell_w / 2, cy + cell_h / 2 + (ln - 0.5) * 80),
                   line, f_center, "#ffffff", stroke_fill="#4a0000", stroke_width=5)

    # 四角小标签（corner_labels 长度 4，顺序：左上/右上/左下/右下）
    if corner_labels and len(corner_labels) == 4:
        f_tag = _load_font(30)
        tag_pos = [
            (pad, start_y + pad),
            (CANVAS_W - pad, start_y + pad),
            (pad, start_y + 2 * (cell_h + pad) + pad),
            (CANVAS_W - pad, start_y + 2 * (cell_h + pad) + pad),
        ]
        for (tx, ty), label in zip(tag_pos, corner_labels):
            _draw_text(draw, (tx, ty + 20), label, f_tag, "#ffffff",
                       stroke_fill="#000000", stroke_width=3,
                       anchor="mm")
    return canvas


# ---------- 模板 3：单图 + 大字利益点 ----------
def single_text(image: Image.Image, headline: str, sub: str | None = None) -> Image.Image:
    """
    单张产品图打底 + 中部大字利益点（如「全品类价目表」「茶礼全部批发价」）。
    文字区压深色渐变条保证可读性。
    """
    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H))
    bg = _cover(image, CANVAS_W, CANVAS_H)
    canvas.paste(bg, (0, 0))
    draw = ImageDraw.Draw(canvas)

    # 中部深色渐变条（下深上浅）
    bar_h = 360
    y0 = (CANVAS_H - bar_h) // 2
    for i in range(bar_h):
        alpha = int(120 + 120 * (i / bar_h))   # 越往下越深
        draw.line([(0, y0 + i), (CANVAS_W, y0 + i)], fill=(0, 0, 0, alpha))

    f_main = _load_font(96)
    lines = _wrap_text(headline, 8)
    n = len(lines)
    for ln, line in enumerate(lines):
        yy = y0 + bar_h / 2 + (ln - (n - 1) / 2) * 110
        _draw_text(draw, (CANVAS_W / 2, yy), line, f_main, "#ffffff",
                   stroke_fill="#8B0000", stroke_width=6)

    if sub:
        f_sub = _load_font(40)
        _draw_text(draw, (CANVAS_W / 2, y0 + bar_h - 70), sub, f_sub,
                   "#ffe9a8", stroke_fill="#000000", stroke_width=2)
    return canvas


# ---------- 模板 4：系列化拼图（对标过关版式：同款多角度+居中大字） ----------
def series_grid(images: list[Image.Image], line1: str, line2: str) -> Image.Image:
    """
    2x2 同款多角度拼图（用户验收版式，见《拼图复盘与模板规范》）：
      - 格间 6px 白缝；每格 = 同一款产品不同视角/动作
      - 标题水平居中：第一行 92px @42% 高度、第二行 104px @58%（横跨画面中心线）
      - 白字细描边（4px），无横幅/无标签条/无大黑底
    images: 恰好 4 张（同系列多角度，顺序即展示顺序）
    """
    assert len(images) == 4, "系列化拼图需要恰好 4 张同系列素材"
    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), "#ffffff")
    draw = ImageDraw.Draw(canvas)
    gap = 6
    cell_w = (CANVAS_W - 3 * gap) // 2
    cell_h = (CANVAS_H - 3 * gap) // 2
    pos = [(0, 0), (cell_w + gap, 0), (0, cell_h + gap), (cell_w + gap, cell_h + gap)]
    for img, (x, y) in zip(images, pos):
        canvas.paste(_cover(img, cell_w, cell_h), (x, y))
    draw = ImageDraw.Draw(canvas)
    f1 = _load_font(92)    # 实测对标实帖 95-105px
    f2 = _load_font(104)
    # 第一行 42% 高（1440×0.42≈605 略修），第二行 58%（835）
    _draw_text(draw, (CANVAS_W / 2, int(CANVAS_H * 0.42)), line1, f1, "#ffffff",
               stroke_fill="#222222", stroke_width=4, shadow=False)
    _draw_text(draw, (CANVAS_W / 2, int(CANVAS_H * 0.58)), line2, f2, "#ffffff",
               stroke_fill="#222222", stroke_width=4, shadow=False)
    return canvas


# ---------- 组装导出 ----------
def compose(images_paths: list[str], template: str, labels: list[str] | None = None,
            center_text: str | None = None, headline: str | None = None,
            title: str | None = None, corner_labels: list[str] | None = None,
            line1: str | None = None, line2: str | None = None,
            out_dir: str | Path | None = None, out_name: str = "cover.jpg") -> str:
    """统一入口：读图 → 按模板拼 → 导出，返回输出文件路径"""
    imgs = [Image.open(p).convert("RGB") for p in images_paths]
    if template == "four_grid":
        result = four_grid(imgs[:4], labels or ["节日茶礼", "企业团购", "烟酒批发", "旅游特产"], title=title)
    elif template == "nine_grid":
        result = nine_grid(imgs[:9], center_text or "茶礼定制", corner_labels=corner_labels)
    elif template == "single_text":
        result = single_text(imgs[0], headline or "", sub=title)
    elif template == "series_grid":
        result = series_grid(imgs[:4], line1 or "武汉特色宝藏伴手礼", line2 or "送礼首选！")
    else:
        raise ValueError(f"未知模板: {template}")

    out_dir = Path(out_dir) if out_dir else Path("output")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / out_name
    result.save(out_path, "JPEG", quality=85)
    return str(out_path)


# ---------- 演示（样例验证） ----------
if __name__ == "__main__":
    import tempfile
    tmp = Path(tempfile.gettempdir())
    # 造 4 张纯色样例图
    demo_paths = []
    for i, color in enumerate([(180, 30, 30), (20, 110, 60), (200, 150, 40), (60, 80, 160)]):
        p = tmp / f"demo_{i}.jpg"
        Image.new("RGB", (800, 800), color).save(p, "JPEG")
        demo_paths.append(str(p))

    out = Path(os.path.join(os.path.dirname(__file__), "..", "output", "demo"))
    print("四宫格 →", compose(
        demo_paths, "four_grid",
        labels=["节日茶礼", "企业团购", "烟酒批发", "旅游特产"],
        title="送礼就送它❗直接被长辈爆夸❗", out_dir=out, out_name="four_grid_demo.jpg"))
    print("九宫格 →", compose(
        demo_paths, "nine_grid", center_text="茶礼定制",
        corner_labels=["恩施玉露", "利川红", "岁安", "歡喜"],
        out_dir=out, out_name="nine_grid_demo.jpg"))
    print("单图大字 →", compose(
        demo_paths, "single_text", headline="全品类价目表", title="茶礼全部批发价",
        out_dir=out, out_name="single_demo.jpg"))
