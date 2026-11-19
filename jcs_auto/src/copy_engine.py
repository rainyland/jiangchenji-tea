# -*- coding: utf-8 -*-
"""
copy_engine.py — 文案引擎
职责：
  1. 标题公式库：场景+利益点组合（源自江陈记现有爆款）
  2. 5 段式正文模板：钩子/产品亮点/场景/福利引导/标签
  3. 账号差异化：替换开头词、emoji、句式、标签顺序（防重复检测）
  4. 广告法敏感词过滤（最/第一/顶级等）
"""
import hashlib
import json
import random
from pathlib import Path

# ---------- 敏感词（广告法/平台禁用，可扩展） ----------
# 用复合词而非单字"最"：避免误伤"最后/最近/最全"等普通用语
BANNED_WORDS = [
    "最好", "最优", "最佳", "最顶级", "最优惠", "最便宜", "最实惠", "性价比最高",
    "国家级", "全网唯一", "绝无仅有", "销量第一", "第一品牌", "世界领先",
    "包治", "根治", "治病", "治疗", "药到病除", "100%", "百分百有效",
    "史无前例", "极致", "万能", "顶配",
]

# ---------- 标题公式库（按店家 2026-10-28 需求重构） ----------
# 强制规则：标题前 10 个字必须出现核心高权重大词（湖北特产/武汉伴手礼）
# 结构：核心大词 + 精准长尾词 + 场景 + 情绪钩子；每篇覆盖 1 核心大词 + 1 长尾词
CORE_WORDS = ["武汉伴手礼", "湖北特产"]   # 核心大词（最高权重，标题前10字强制）
LONG_TAILS = ["茶叶礼盒", "恩施玉露茶礼", "利川红礼盒", "楚汉茶礼", "双拼茶礼"]  # 精准长尾词

HEADLINE_FORMULAS = {
    "送礼": [
        "武汉伴手礼｜{品类}，走亲访友送超有面儿✨",
        "湖北特产{品类}，过年送礼被长辈爆夸❗",
        "武汉伴手礼送{品类}，体面又实用💛",
    ],
    "企业": [
        "武汉伴手礼｜商务伴手礼选{品类}，客户都夸",
        "湖北特产{品类}，企业定制伴手礼首选",
        "武汉伴手礼{品类}，商务出行拿得出手",
    ],
    "旅游": [
        "武汉伴手礼｜来武汉必带的{品类}，返程必备",
        "湖北特产{品类}，武汉旅游伴手礼不踩雷",
        "武汉伴手礼{品类}，游客返程人手一份",
    ],
    "门店": [
        "武汉伴手礼｜门店实拍{品类}，到店可试喝",
        "湖北特产{品类}，武汉实体店随时可买",
        "武汉伴手礼{品类}，同城配送到家",
    ],
}

# 差异化词库（温柔高级、博主种草口吻；同一天多账号不能同开头）
OPENERS = ["在武汉待了这么久", "每次有朋友来武汉", "发现一个宝藏", "真心建议", "逛了一圈还是"]
EMOJIS = ["🍵", "🎁", "✨", "🔥", "💛", "❗", "💯", "🌆", "🍃", "😍"]

# 标签库（按店家黄金配比分类：2核心大词 + 3精准长尾 + 3场景词 + 2同城热词）
TAG_CORE = ["#湖北特产", "#武汉伴手礼", "#武汉特产", "#武汉礼物"]
TAG_LONGTAIL = ["#茶叶礼盒", "#恩施玉露", "#利川红", "#茶礼定制", "#伴手茶礼", "#楚汉茶礼", "#双拼茶礼"]
TAG_SCENE = ["#武汉旅游", "#送礼必备", "#返程伴手礼", "#走亲访友", "#商务伴手礼", "#春节送礼"]
TAG_CITY = ["#武汉探店", "#武汉美食", "#武汉吃喝玩乐", "#武汉生活"]

# 正文三段式埋词（开头前3行埋核心词1-2次 → 中间卖点+场景长尾 → 结尾核心词强化+同城引流）
OPENINGS = {  # 开头：含核心大词，匹配搜索痛点
    "送礼": "武汉伴手礼我挑了很久，最后还是选了它",
    "旅游": "返程前来武汉，湖北特产伴手礼纠结半天定了这款",
    "企业": "商务送礼要体面，武汉伴手礼这几款很稳",
    "门店": "在武汉找湖北特产伴手礼，这家店现货最全",
}
ENDINGS = {  # 结尾：核心词二次强化 + 温和同城引流
    "送礼": "这份武汉伴手礼，送长辈送亲友都拿得出手",
    "旅游": "回程带上这份武汉伴手礼，朋友收到都问链接",
    "企业": "客户收到这份湖北特产，合作都好谈了几分",
    "门店": "在武汉随时能买的湖北特产，回购率很高",
}
SCENE_LINES = {  # 场景句（中间段钩子，含核心词/场景长尾词）
    "送礼": "走亲访友拎一盒，武汉伴手礼长辈当场拆开就夸",
    "旅游": "武汉旅游返程必备，湖北特产伴手礼行李箱正好放下",
    "企业": "商务出行带上湖北特产，客户眼前一亮",
    "门店": "进店就能试喝，武汉伴手礼满意再带走",
}

# 正文模板（三段式埋词，{}-占位符）：
# 段1 开头前3行：核心大词 1-2 次（core_opening）
# 段2 中间主体：场景句 + 卖点 ①②③ + 场景使用（scene_line/use_scene 含场景长尾词）
# 段3 结尾：核心词二次强化（ending）+ 温和同城引流（门店信息）
BODY_TEMPLATE = (
    "{opener}，{core_opening}\n\n"
    "{scene_line}，真的很难不爱\n\n"
    "【为什么选它】\n"
    "① {point1}\n"
    "② {point2}\n"
    "③ {point3}\n\n"
    "{use_scene}\n\n"
    "{ending}\n"
    "📍江陈记茶业（武汉），门店可试喝\n"
    "评论区扣「{keyword}」帮你挑合适的那款～\n\n"
    "{tags}"
)


class CopyEngine:
    def __init__(self, templates_path: str | Path | None = None):
        """templates_path: 可选外部模板 JSON（config/copy_templates.json），便于商家不改代码调文案"""
        self.headlines = HEADLINE_FORMULAS
        self.body = BODY_TEMPLATE
        self.openings = OPENINGS
        self.endings = ENDINGS
        self.scene_lines = SCENE_LINES
        self.tag_core, self.tag_longtail, self.tag_scene, self.tag_city = TAG_CORE, TAG_LONGTAIL, TAG_SCENE, TAG_CITY
        if templates_path and Path(templates_path).exists():
            data = json.loads(Path(templates_path).read_text(encoding="utf-8"))
            self.headlines = data.get("headlines", HEADLINE_FORMULAS)
            self.body = data.get("body", BODY_TEMPLATE)
            self.openings = data.get("openings", OPENINGS)
            self.endings = data.get("endings", ENDINGS)
            self.scene_lines = data.get("scene_lines", SCENE_LINES)
            tags = data.get("tags", {})
            self.tag_core = tags.get("core", TAG_CORE)
            self.tag_longtail = tags.get("longtail", TAG_LONGTAIL)
            self.tag_scene = tags.get("scene", TAG_SCENE)
            self.tag_city = tags.get("city", TAG_CITY)

    # ---------- 敏感词过滤 ----------
    @staticmethod
    def filter_banned(text: str) -> tuple[str, list[str]]:
        """剔除/标记敏感词，返回 (清洗后文本, 命中词列表)"""
        hits = [w for w in BANNED_WORDS if w in text]
        cleaned = text
        for w in hits:
            cleaned = cleaned.replace(w, "**")
        return cleaned, hits

    # ---------- 标题生成 ----------
    def make_headline(self, scenario: str, product: str, seed: int | None = None,
                      obj: str = "长辈", num: str = "100万", client: str = "中建三局",
                      variant: int | None = None) -> str:
        """
        variant: 账号序号（可选）。提供时按序号错位选模板，
        同一批不同账号（variant 不同）必然得到不同标题模板，杜绝撞车；
        不提供时保持原随机行为（向后兼容测试）。
        """
        rng = random.Random(seed)   # 同 seed 可复现，便于测试
        formulas = self.headlines.get(scenario, self.headlines["送礼"])
        if variant is not None:
            tpl = formulas[variant % len(formulas)]
        else:
            tpl = rng.choice(formulas)
        return tpl.format(品类=product, 对象=obj, 数字=num, 客户=client)

    # ---------- 正文生成（三段式埋词 + 标签黄金配比） ----------
    @staticmethod
    def _pick(pool: list[str], n: int, variant: int | None, rng: random.Random) -> list[str]:
        """从池中选 n 个：variant 提供时错位切片（不同账号不同），否则随机"""
        if n <= 0 or not pool:
            return []
        if variant is not None:
            start = (variant * 7 + 3) % len(pool)
            return (pool[start:] + pool[:start])[:n]
        return rng.sample(pool, min(n, len(pool)))

    def _golden_tags(self, rng: random.Random, variant: int | None, tag_count: int) -> list[str]:
        """标签黄金配比：2核心大词 + 3精准长尾 + 3场景词 + 2同城热词（共10）"""
        if tag_count >= 10:
            n_core, n_long, n_scene, n_city = 2, 3, 3, 2
        else:
            n_core = min(2, max(1, tag_count // 4))
            rest = tag_count - n_core
            n_long = (rest + 1) // 2
            n_scene = (rest - n_long + 1) // 2
            n_city = rest - n_long - n_scene
        tags = (self._pick(self.tag_core, n_core, variant, rng)
                + self._pick(self.tag_longtail, n_long, variant, rng)
                + self._pick(self.tag_scene, n_scene, variant, rng)
                + self._pick(self.tag_city, n_city, variant, rng))
        return tags

    def make_body(self, *, scenario: str, product: str, points: list[str],
                  use_scene: str, seed: int | None = None,
                  keyword: str = "1", opener: str | None = None,
                  tag_count: int = 10, variant: int | None = None) -> tuple[str, str]:
        rng = random.Random(seed)
        if opener is None:
            # 不同账号（variant 不同）取不同开头词，保证开头不撞
            opener = OPENERS[variant % len(OPENERS)] if variant is not None else rng.choice(OPENERS)
        # 三段式埋词内容：开头含核心大词 / 场景句 / 结尾核心词二次强化
        core_opening = OPENINGS.get(scenario, OPENINGS["送礼"])
        scene_line = SCENE_LINES.get(scenario, SCENE_LINES["送礼"])
        ending = ENDINGS.get(scenario, ENDINGS["送礼"])
        # 卖点顺序按账号错位轮换（① ② ③内容顺序不同，拉低账号间相似度）
        if variant is not None and len(points) > 1:
            shift = variant % len(points)
            points = points[shift:] + points[:shift]
        # 标签黄金配比（2核心大词+3精准长尾+3场景词+2同城热词）
        tags = self._golden_tags(rng, variant, tag_count)
        tags_str = " ".join(tags)
        text = self.body.format(
            opener=opener,
            core_opening=core_opening,
            scene_line=scene_line,
            point1=points[0] if len(points) > 0 else "",
            point2=points[1] if len(points) > 1 else "",
            point3=points[2] if len(points) > 2 else "",
            use_scene=use_scene,
            ending=ending,
            keyword=keyword,
            tags=tags_str,
        )
        cleaned, hits = self.filter_banned(text)
        if hits:
            cleaned += "\n[⚠️敏感词已替换: " + ", ".join(hits) + "]"
        return cleaned, tags_str

    # ---------- 去重指纹（供风控相似度比对） ----------
    @staticmethod
    def text_fingerprint(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    # ---------- 可变核心提取（供风控相似度比对） ----------
    @staticmethod
    def core_text(body: str) -> str:
        """
        提取文案的可变核心用于相似度比对：
        去掉门店地址、引导语等品牌固定段落（同一商家多账号本就相同，不算雷同），
        只比对开头、标题、卖点、场景句、标签这些真正需要差异化的部分。
        """
        cut = body.find("\n📍江陈记茶业")
        if cut >= 0:
            body = body[:cut]
        # 去掉「【X场景…】」固定壳行（兼容旧模板）
        lines = [ln for ln in body.split("\n")
                 if not ln.strip().startswith("【")]
        return "\n".join(lines).strip()


if __name__ == "__main__":
    eng = CopyEngine()
    for sc in ["送礼", "企业", "旅游", "门店"]:
        body, tags = eng.make_body(
            scenario=sc, product="恩施玉露茶礼盒",
            points=["明前头采，海苔香", "蒸青工艺，湖北恩施", "礼盒大气，送人有面"],
            use_scene="过年走亲戚拎一盒，长辈当场拆开就夸", seed=1, keyword="1")
        print(f"--- {sc} ---")
        print(body)
        print()
