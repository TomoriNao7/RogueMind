"""规则引擎 — 基于抓位榜单的招募推荐和精二推荐."""

import json
from pathlib import Path
from typing import Optional

from ..models.schemas import GameState, RecommendResult, RecommendItem, PlayStyle

DATA_DIR = Path(__file__).parent.parent.parent / "data"

_pick_list: list[dict] = []
_loaded = False


def _load():
    """加载抓位榜单."""
    global _pick_list, _loaded
    if _loaded:
        return
    path = DATA_DIR / "pick_priority.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            _pick_list = json.load(f)
    _loaded = True


# ═══════════════════ 阵容分析 ═══════════════════

def _analyze_roster(state: GameState) -> dict:
    """分析当前阵容的短板和缺口.

    Returns:
        {
            "classes_have": {"近卫": 3, "先锋": 1, ...},
            "classes_missing": ["重装", "医疗", ...],
            "roles_have": {"输出", "爆费", ...},
            "roles_missing": ["治疗", "防护", ...],
            "operator_count": 总数,
            "has_e2_candidates": [可精二的干员列表],
            "is_rich": bool 是否富局（源石锭>30）
        }
    """
    classes_have = {}
    roles_have = set()
    e2_candidates = []

    from .data_loader import get_operator_by_id

    for po in state.operators:
        op = get_operator_by_id(po.operator_id)
        if not op:
            continue

        cls = op.get("class", "")
        classes_have[cls] = classes_have.get(cls, 0) + 1

        # 收集当前干员的标签作为已覆盖的能力
        for tag in op.get("tags", []):
            roles_have.add(tag)

        # 精一满级可精二
        if po.elite == 1 and po.level >= 70:
            e2_candidates.append(po.operator_id)

    # 分析缺口
    all_classes = {"先锋", "近卫", "重装", "狙击", "术师", "医疗", "辅助", "特种"}
    classes_missing = [c for c in all_classes if c not in classes_have]

    # 核心能力
    core_roles = {"治疗", "防护", "爆费", "控制"}
    roles_missing = [r for r in core_roles if r not in roles_have]

    # 判断穷局/富局
    is_rich = state.resources.originium_ingot >= 30

    return {
        "classes_have": classes_have,
        "classes_missing": classes_missing,
        "roles_have": roles_have,
        "roles_missing": roles_missing,
        "operator_count": len(state.operators),
        "e2_candidates": e2_candidates,
        "is_rich": is_rich,
    }


# ═══════════════════ 招募推荐 ═══════════════════

def recommend_recruit(state: GameState) -> RecommendResult:
    """基于阵容分析和抓位榜单，推荐下一步应招募的干员."""
    _load()
    analysis = _analyze_roster(state)
    roster = state.operators

    # 已持有的干员 ID 集合
    have_ids = {po.operator_id for po in roster}
    have_names = set()
    from .data_loader import get_operator_by_id
    for oid in have_ids:
        op = get_operator_by_id(oid)
        if op:
            have_names.add(op.get("name", ""))

    # 可用的希望
    hope = state.resources.hope

    scored = []
    for entry in _pick_list:
        name = entry["name"]
        if name in have_names:
            continue  # 已持有，跳过

        tier = entry["pick_tier"]
        cls = entry["class"]
        roles = entry["roles"]
        note = entry["note"]

        # 基础得分：tier 越低越好（0=100, 1=85, 2=60, 3=30, 4=10）
        tier_scores = {0: 100, 1: 85, 2: 60, 3: 30, 4: 10}
        score = tier_scores.get(tier, 5)

        reasons = []

        # 加分1：阵容缺少该职业
        if cls in analysis["classes_missing"]:
            score += 15
            reasons.append(f"阵容缺少{cls}职业")

        # 加分2：干员能力覆盖了阵容缺口
        for role in roles:
            if role in analysis["roles_missing"]:
                score += 10
                reasons.append(f"可提供{role}能力")
                break

        # 加分3：一抓干员在穷局更优先
        if tier == 0 and not analysis["is_rich"]:
            score += 5
            reasons.append("穷局兜底首选")

        # 减分：一抓但需要精二，而玩家希望不足
        if tier <= 1 and entry.get("need_e2", False) and hope < 9:
            score -= 15

        # 行动风格调整
        if state.style == PlayStyle.ECO:
            if "增益" in roles or "兜底" in roles:
                score += 5
        elif state.style == PlayStyle.INFINITE:
            if "经济" in roles or "源石锭" in roles:
                score += 5

        scored.append({
            "operator_id": "",  # 后续通过名称匹配填充
            "name": name,
            "class": cls,
            "score": max(score, 0),
            "reason": note + "。" + "；".join(reasons) if reasons else "",
            "tier": tier,
        })

    # 按得分排序
    scored.sort(key=lambda x: x["score"], reverse=True)

    # 匹配 operator_id
    for s in scored:
        op = _find_op_by_name(s["name"])
        if op:
            s["operator_id"] = op["id"]

    # 只返回得分为正的
    scored = [s for s in scored if s["score"] > 0]

    items = []
    for i, s in enumerate(scored[:8]):
        items.append(RecommendItem(
            rank=i + 1,
            id=s["operator_id"] or s["name"],
            name=s["name"],
            reason=s["reason"][:200],
            score=min(s["score"], 100),
        ))

    analysis_text = _build_recruit_analysis(analysis)

    return RecommendResult(
        type="recruit",
        recommendations=items,
        analysis=analysis_text,
        source="rule_engine",
    )


def _build_recruit_analysis(analysis: dict) -> str:
    """生成招募推荐的整体分析文本."""
    parts = []
    classes_missing = analysis["classes_missing"]
    roles_missing = analysis["roles_missing"]

    if classes_missing:
        parts.append(f"当前阵容缺少{', '.join(classes_missing)}职业")
    if roles_missing:
        parts.append(f"缺少{', '.join(roles_missing)}能力")

    if not parts:
        parts.append("当前阵容较为均衡，可根据抓位榜单优先补充一抓干员")

    parts.append(f"已持有{analysis['operator_count']}名干员")
    if analysis["is_rich"]:
        parts.append("当前源石锭充裕（富局），可考虑补强任意方向")
    else:
        parts.append("当前源石锭较少（穷局），建议优先抓兜底能力强的干员")

    return "；".join(parts)


# ═══════════════════ 精二推荐 ═══════════════════

def recommend_promote(state: GameState) -> RecommendResult:
    """推荐最值得精二的干员."""
    _load()
    analysis = _analyze_roster(state)
    roster = state.operators

    from .data_loader import get_operator_by_id

    scored = []
    for po in roster:
        if po.elite >= 2:
            continue  # 已经精二了
        if po.elite == 0:
            continue  # 精0不推荐精二
        if po.level < 70:
            continue  # 等级不够

        op = get_operator_by_id(po.operator_id)
        if not op:
            continue
        name = op.get("name", "")

        # 查找抓位榜单
        entry = _find_pick_entry(name)
        if not entry:
            continue

        tier = entry["pick_tier"]
        need_e2 = entry.get("need_e2", False)

        # 基础得分
        score = 60 - tier * 15  # tier0=60, tier1=45, tier2=30, tier3=15
        if need_e2:
            score += 25  # 榜单明确标注精二发力，加成多

        reasons = [entry["note"]]

        scored.append({
            "operator_id": po.operator_id,
            "name": name,
            "score": min(score + 10, 100),
            "reason": entry["note"][:200],
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    scored = [s for s in scored if s["score"] > 0]

    items = []
    for i, s in enumerate(scored[:5]):
        items.append(RecommendItem(
            rank=i + 1,
            id=s["operator_id"],
            name=s["name"],
            reason=s["reason"][:200],
            score=s["score"],
        ))

    return RecommendResult(
        type="promote",
        recommendations=items,
        analysis=f"当前阵容有{len(scored)}名干员可精二，按抓位和精二收益排序推荐",
        source="rule_engine",
    )


# ═══════════════════ 藏品推荐 ═══════════════════

def recommend_relic(state: GameState) -> RecommendResult:
    """基于阵容缺口和资源状态推荐应获取的藏品.

    逻辑：分析阵容短板 → 匹配藏品标签 → 按缺口优先排序。
    同时考虑行动风格和当前资源状况。
    """
    _load()
    analysis = _analyze_roster(state)
    have_relics = set(state.relics)

    from .data_loader import get_relics, get_relic_by_id

    all_relics = get_relics()

    scored = []
    for relic in all_relics:
        if relic["id"] in have_relics:
            continue

        tags = relic.get("tags", [])
        rarity = relic.get("rarity", 1)
        # 基础分 = rarity * 15，稀有度越高基础分越高（rarity 即强度评分）
        score = rarity * 15
        reasons = []

        # 阵容缺口匹配
        if "经济" in tags or "源石锭" in tags:
            if analysis["is_rich"]:
                score += 5
                reasons.append("富局可进一步滚经济")
            elif state.resources.originium_ingot < 10:
                score += 15
                reasons.append("急需补充经济")

        if "输出" in tags or "攻击" in tags:
            if "输出" in analysis["roles_missing"]:
                score += 15
                reasons.append("阵容输出不足")

        if "防御" in tags or "生存" in tags:
            if "防护" in analysis["roles_missing"]:
                score += 15
                reasons.append("阵容缺少防护")
            if state.resources.hp <= 3:
                score += 10
                reasons.append("生命值危险，急需生存")

        if "治疗" in tags:
            if "治疗" in analysis["roles_missing"]:
                score += 15
                reasons.append("阵容缺少治疗")

        if "技力" in tags or "技能" in tags:
            score += 8
            reasons.append("技能循环提升")

        if "攻速" in tags:
            score += 8
            reasons.append("攻速提升")

        if "费用" in tags or "先锋" in tags:
            if "爆费" in analysis["roles_missing"]:
                score += 12
                reasons.append("爆费能力不足")

        if "部署" in tags or "携带" in tags:
            if analysis["operator_count"] < 4:
                score += 12
                reasons.append("干员数量偏少，需要部署/携带加成")

        if "招募" in tags or "希望" in tags:
            if state.resources.hope < 5:
                score += 12
                reasons.append("希望紧张，减招募成本")

        if "商店" in tags:
            if state.resources.originium_ingot >= 15:
                score += 8
                reasons.append("源石锭充裕，商店收益高")

        if "再部署" in tags:
            score += 5
            reasons.append("再部署加速")

        # 行动风格调整
        if state.style.value == "电表倒转":
            if "经济" in tags or "源石锭" in tags or "商店" in tags:
                score += 10
        elif state.style.value == "发育流":
            if "招募" in tags or "希望" in tags or "输出" in tags or "生存" in tags:
                score += 5
        elif state.style.value == "速通流":
            if "输出" in tags or "再部署" in tags or "攻速" in tags:
                score += 8

        # 有协同藏品的加分
        synergies = relic.get("synergies", [])
        if synergies:
            matched = [s for s in synergies if s in have_relics]
            if matched:
                score += 10
                reasons.append(f"与已持有藏品协同")

        # 标签太少或太泛的降分
        if not tags:
            score -= 20

        scored.append({
            "id": relic["id"],
            "name": relic["name"],
            "score": min(score, 100),
            "reason": relic.get("effect", "") + ("。" + "；".join(reasons) if reasons else ""),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    scored = [s for s in scored if s["score"] > 0]

    items = []
    for i, s in enumerate(scored[:8]):
        items.append(RecommendItem(
            rank=i + 1,
            id=s["id"],
            name=s["name"],
            reason=s["reason"][:200],
            score=s["score"],
        ))

    # 生成分析文本
    analysis_text = "根据当前阵容缺口和资源状况推荐藏品"
    if analysis["roles_missing"]:
        analysis_text += f"，阵容缺少{', '.join(analysis['roles_missing'])}能力"
    if analysis["classes_missing"]:
        analysis_text += f"，缺少{', '.join(analysis['classes_missing'])}职业"

    return RecommendResult(
        type="relic",
        recommendations=items,
        analysis=analysis_text,
        source="rule_engine",
    )


# ═══════════════════ 辅助函数 ═══════════════════

def _find_pick_entry(name: str) -> Optional[dict]:
    """通过干员名查找抓位条目."""
    _load()
    for entry in _pick_list:
        if entry["name"] == name:
            return entry
    return None


def _find_op_by_name(name: str) -> Optional[dict]:
    """通过干员名查找干员数据."""
    from .data_loader import get_operator_by_name
    return get_operator_by_name(name)


# ═══════════════════ 通宝推荐 ═══════════════════

_coin_priority: list[dict] = []
_coin_loaded = False


def _load_coins():
    """加载通宝优先级数据."""
    global _coin_priority, _coin_loaded
    if _coin_loaded:
        return
    path = DATA_DIR / "coin_priority.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            _coin_priority = json.load(f)
    _coin_loaded = True


def recommend_coin(state: GameState) -> RecommendResult:
    """推荐应保留或获取的通宝.

    基于界园通宝评价，按 tier 排序（0=必拿, 1=推荐拿, 2=一般, 3=过渡, 4=不推荐, 5=直接丢）。
    已持有的通宝标注其评价，未持有的推荐必拿通宝。
    """
    _load_coins()
    current_coins = set(state.coinbox.coins) if state.coinbox else set()

    # 已持有通宝的评价
    have_scored = []
    for coin_id in current_coins:
        name = _coin_name_by_id(coin_id)
        entry = _find_coin_entry(name)
        if entry:
            tier = entry["tier"]
            tier_labels = {0: "必拿", 1: "推荐", 2: "一般", 3: "过渡", 4: "不推荐", 5: "建议丢弃"}
            have_scored.append({
                "coin_id": coin_id,
                "name": name,
                "tier": tier,
                "note": entry["note"],
                "action": "丢弃" if tier >= 5 else ("保留" if tier <= 1 else "可替换"),
            })

    have_scored.sort(key=lambda x: x["tier"])

    # 推荐未持有的高优先级通宝
    recommended = []
    have_names = {c["name"] for c in have_scored}
    for entry in _coin_priority:
        if entry["name"] not in have_names and entry["tier"] <= 1:
            recommended.append(entry)

    recommended.sort(key=lambda x: x["tier"])

    items = []
    # 先展示已持有的评价
    for i, c in enumerate(have_scored[:10]):
        items.append(RecommendItem(
            rank=i + 1,
            id=c["coin_id"],
            name=c["name"],
            reason=f"[{c['action']}] {c['note']}"[:200],
            score=100 - c["tier"] * 20,
        ))

    analysis_parts = []
    bad_coins = [c for c in have_scored if c["tier"] >= 5]
    if bad_coins:
        analysis_parts.append(f"建议丢弃: {', '.join(c['name'] for c in bad_coins)}")

    top_picks = [r["name"] for r in recommended[:5]]
    if top_picks:
        analysis_parts.append(f"推荐获取: {', '.join(top_picks)}")

    if not analysis_parts:
        analysis_parts.append("当前通宝配置合理")

    return RecommendResult(
        type="coin",
        recommendations=items,
        analysis="；".join(analysis_parts),
        source="rule_engine",
    )


def _find_coin_entry(name: str) -> Optional[dict]:
    """通过通宝名查找优先级条目."""
    _load_coins()
    for entry in _coin_priority:
        if entry["name"] == name:
            return entry
    return None


def _coin_name_by_id(coin_id: str) -> str:
    """通过 ID 查找通宝名称."""
    from .data_loader import get_coin_by_id
    coin = get_coin_by_id(coin_id)
    return coin["name"] if coin else coin_id
