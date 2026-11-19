# -*- coding: utf-8 -*-
"""
main.py — 江陈记茶业 · 小红书多账号自动发布 主入口
用法（部署在商家电脑/服务器，配合系统定时任务每天执行一次）：
  python src/main.py --dry-run          # 预演：生成当日队列和待发包，不实际发布
  python src/main.py                    # 正式运行：按队列发布到点任务
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from asset_lib import AssetLibrary          # noqa: E402
from copy_engine import CopyEngine          # noqa: E402
from image_pipeline import compose          # noqa: E402
from risk_control import RiskControl        # noqa: E402
from scheduler import DailyScheduler        # noqa: E402

CONFIG = ROOT / "config" / "config.example.json"


def load_config(path: Path = CONFIG) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_daily_pack(cfg: dict, risk: RiskControl, assets: AssetLibrary,
                     copy: CopyEngine, out_dir: Path) -> list[dict]:
    """为当日队列每一条生成（图+文案）待发包，全部过风控校验"""
    scheduler = DailyScheduler(CONFIG)
    queue = scheduler.build_schedule()
    packs = []
    batch_used: set[str] = set()      # 本批队列已占用素材 hash（账号间图片互斥）
    batch_copies: list[str] = []      # 本批队列已生成文案（相似度互比）
    template = cfg.get("template", "four_grid")
    need = {"four_grid": 4, "nine_grid": 9, "series_grid": 4, "single_text": 1}.get(template, 1)   # 模板所需最少图数
    series_rotation = cfg.get("series_rotation", [])   # 系列轮换（同款多角度拼图）
    for acc_idx, item in enumerate(queue):
        acc_id = item["account"]
        # 风控预检
        ok_freq, msg_freq = risk.check_frequency(acc_id)
        ok_sus, msg_sus = risk.check_suspension(acc_id)
        if not (ok_freq and ok_sus):
            print(f"[跳过] {item['name']}：{msg_freq or msg_sus}")
            continue
        # 选素材（未用过的图，且不与本批其他账号重复）
        assets.scan_assets()
        pool = assets.load_hashes()
        if template == "series_grid" and series_rotation:
            # 按系列轮换：同一账号系列内挑图（同款产品多角度）
            series = series_rotation[acc_idx % len(series_rotation)]
            candidates = [c for c in pool
                          if c["cat"] == cfg.get("material_priority", "01_产品线") and c.get("sub") == series]
            if not candidates:
                print(f"[跳过] {item['name']}：系列「{series}」无素材")
                continue
        else:
            candidates = [c for c in pool if c["cat"] == cfg.get("material_priority", "01_产品线")] or pool
        unused = assets.pick_unused(candidates, limit=need, exclude=batch_used)
        if len(unused) < need:
            print(f"[跳过] {item['name']}：素材不足（{template} 需 {need} 张，可用仅 {len(unused)} 张）")
            continue
        imgs = [u["path"] for u in unused]
        batch_used.update(u["hash"] for u in unused)
        # 生成文案（seed 用日期+账号序号：同一天各账号固定、账号间不同，且跨进程稳定）
        seed = int(item["publish_time"][:10].replace("-", "")) * 100 + acc_idx
        # 场景按账号轮换（送礼/旅游/企业/门店 → 开头结尾埋词段不同，账号间文案相似度大幅拉低）
        scenario_rotation = cfg.get("scenario_rotation", [cfg.get("scenario", "送礼")])
        scenario = scenario_rotation[acc_idx % len(scenario_rotation)]
        # 卖点组/场景句：按账号序号轮换不同组合，保证账号间内容真正不同
        default_points = ["明前头采，海苔香", "蒸青工艺，湖北恩施", "礼盒大气，送人有面"]
        points_sets = cfg.get("points_sets", [cfg.get("points", default_points)])
        use_scenes = cfg.get("use_scenes", [cfg.get("use_scene", "过年走亲戚拎一盒，长辈当场拆开就夸")])
        pts = points_sets[acc_idx % len(points_sets)]
        usc = use_scenes[acc_idx % len(use_scenes)]
        title = copy.make_headline(scenario, cfg.get("product", "恩施玉露茶礼盒"),
                                   seed=seed, variant=acc_idx)
        body, tags = copy.make_body(
            scenario=scenario,
            product=cfg.get("product", "恩施玉露茶礼盒"),
            points=pts,
            use_scene=usc,
            seed=seed,
            keyword=cfg.get("keyword", "1"),
            variant=acc_idx,
        )
        # 文案相似度校验：只比对可变核心（门店/引导语等品牌固定段不计入），≥60% 拦截
        core = copy.core_text(body)
        if batch_copies:
            ok_copy, msg_copy = risk.check_copy(core, batch_copies)
            if not ok_copy:
                print(f"[风控拦截] {item['name']}：{msg_copy}")
                continue
        batch_copies.append(core)
        # 封面：按配置模板生成（series_grid = 系列化拼图：同款多角度 + 居中大字）
        cover_name = f"{acc_id}_{item['publish_time'][11:16].replace(':','')}_cover.jpg"
        cover = compose(
            imgs,
            template=template,
            labels=cfg.get("grid_labels", ["节日茶礼", "企业团购", "烟酒批发", "旅游特产"]),
            title=cfg.get("headline_override"),
            center_text=cfg.get("center_text"),
            headline=cfg.get("headline_override"),
            line1=cfg.get("cover_line1", "武汉特色宝藏伴手礼"),
            line2=cfg.get("cover_line2", "送礼首选！"),
            out_dir=out_dir / item["publish_time"][:10],
            out_name=cover_name,
        )
        # 图片去重
        ok_img, msg_img = risk.check_image(cover)
        if not ok_img:
            continue
        packs.append({**item, "images": [cover], "title": title,
                      "body": body, "tags": tags})
    return packs


def _publish_pack(p: dict, acc_map: dict, risk: RiskControl):
    """发布单条待发包（需 playwright + 账号登录态）"""
    acc = acc_map[p["account"]]
    pub = XhsPublisher(acc, risk)
    result = pub.publish(p["images"], p["title"], p["body"], p["tags"])
    print(json.dumps(result, ensure_ascii=False))
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="预演，不实际发布")
    ap.add_argument("--wait", action="store_true", help="定时模式：按排期到点发布（长驻等待）")
    ap.add_argument("--config", default=str(CONFIG), help="配置文件路径")
    args = ap.parse_args()

    cfg = load_config(Path(args.config))
    assets = AssetLibrary(ROOT / "assets")
    risk = RiskControl(state_path=ROOT / "output" / "logs" / "state.json", asset_lib=assets)
    copy = CopyEngine(ROOT / "config" / "copy_templates.json")
    out_dir = ROOT / "assets" / "04_成图输出"

    if args.dry_run:
        packs = build_daily_pack(cfg, risk, assets, copy, out_dir)
        print(f"[预演] 今日待发布 {len(packs)} 条：")
        for p in packs:
            print(f"  {p['name']}  {p['publish_time'][11:16]}  {p['title'][:24]}  → {p['images'][0]}")
        return

    # 正式运行（发布器需先按 README 配置 playwright + 账号登录态）
    try:
        from publisher import XhsPublisher
    except RuntimeError as e:
        print("[提示]", e)
        print("  dry-run 预演可用；正式发布需先安装 playwright（见 README.md）")
        return

    packs = build_daily_pack(cfg, risk, assets, copy, out_dir)
    acc_map = {a["id"]: a for a in cfg["accounts"]}
    if not args.wait:
        # 立即模式：生成完直接逐个发布（适合部署端定时任务每天跑一次）
        for p in packs:
            _publish_pack(p, acc_map, risk)
        return

    # 定时模式：长驻等待，按排期到点发布（错峰由 scheduler 保证）
    import datetime as _dt
    import time as _time
    remaining = sorted(packs, key=lambda x: x["publish_time"])
    print(f"[定时] 今日队列 {len(remaining)} 条，长驻等待到点发布（Ctrl+C 退出）")
    while remaining:
        now = _dt.datetime.now().astimezone()
        due = [p for p in remaining if _dt.datetime.fromisoformat(p["publish_time"]) <= now]
        if due:
            for p in due:
                print(f"[发布] {p['name']} {p['publish_time'][11:16]}")
                _publish_pack(p, acc_map, risk)
                remaining = [r for r in remaining if r != p]
        else:
            _time.sleep(30)   # 30 秒轮询一次


if __name__ == "__main__":
    main()
