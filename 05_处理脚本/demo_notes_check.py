# -*- coding: utf-8 -*-
"""按店家需求规范生成示例笔记组 + 规则符合度校验。"""
import sys
sys.path.insert(0, r"C:\Users\Lenovo\Desktop\江陈记茶业\jcs_auto")
from src.copy_engine import CopyEngine, CORE_WORDS, LONG_TAILS

eng = CopyEngine(r"C:\Users\Lenovo\Desktop\江陈记茶业\jcs_auto\config\copy_templates.json")

POINTS = ["正宗湖北茶，明前头采", "包装高级，送人倍有面", "轻便好拎，返程不占地"]
SCENES = {
    "送礼": "本地人走亲戚送礼，拎一盒长辈当场拆开就夸",
    "旅游": "武汉旅游必买，行李箱正好放下不占地方",
    "企业": "商务伴手礼，客户拿到手上夸有心了",
    "门店": "同城配送，今天下单明天就能送到手",
}

for i, sc in enumerate(["送礼", "旅游", "企业", "门店"]):
    title = eng.make_headline(sc, "恩施玉露茶礼盒", seed=i, variant=i)
    body, tags = eng.make_body(scenario=sc, product="恩施玉露茶礼盒", points=POINTS,
                               use_scene=SCENES[sc], seed=i, variant=i, keyword=str(i + 1))
    core = eng.core_text(body)
    # 规则校验
    head10 = title[:10]
    hit_core = [w for w in CORE_WORDS if w in title[:10]]
    core_count = sum(body.count(w) for w in CORE_WORDS)
    density = core_count * sum(len(w) for w in CORE_WORDS) / max(1, len(body))
    tag_list = [t for t in tags.split(" ") if t]
    print("=" * 62)
    print(f"【组{i + 1}｜{sc}场景】")
    print("标题:", title)
    print(f"  前10字[{head10}] → 核心大词: {hit_core or '✗缺失'}")
    print(f"  核心词全文出现 {core_count} 次（要求3-5），密度 {density:.1%}（要求3%-5%）")
    print("正文:")
    print(body)
    print()
    print(f"标签({len(tag_list)}个): {tags}")
    print("  配比: 核心", sum(1 for t in tag_list if t in eng.tag_core),
          "| 长尾", sum(1 for t in tag_list if t in eng.tag_longtail),
          "| 场景", sum(1 for t in tag_list if t in eng.tag_scene),
          "| 同城", sum(1 for t in tag_list if t in eng.tag_city))

# 双账号差异化抽查（同一场景两个 variant 不能同标题/同标签）
print()
print("=" * 62)
print("【双账号差异化抽查】variant 0 vs 1（旅游场景）")
t0 = eng.make_headline("旅游", "恩施玉露茶礼盒", seed=0, variant=0)
t1 = eng.make_headline("旅游", "恩施玉露茶礼盒", seed=0, variant=1)
b0, tag0 = eng.make_body(scenario="旅游", product="恩施玉露茶礼盒", points=POINTS, use_scene=SCENES["旅游"], seed=0, variant=0)
b1, tag1 = eng.make_body(scenario="旅游", product="恩施玉露茶礼盒", points=POINTS, use_scene=SCENES["旅游"], seed=0, variant=1)
print("标题A:", t0)
print("标题B:", t1, "→ 不同:", t0 != t1)
print("标签A:", tag0)
print("标签B:", tag1, "→ 不同:", tag0 != tag1)
