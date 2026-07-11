"""Agent 工具定义 — 可供 LLM 调用的函数，用于查询游戏数据和知识库."""

from . import rag, data_loader


# ═══════════════════ 工具执行 ═══════════════════

def execute_tool(name: str, arguments: dict) -> str:
    """执行工具调用，返回结果字符串."""
    if name == "search_knowledge":
        return _search_knowledge(**arguments)
    elif name == "get_operator_info":
        return _get_operator_info(**arguments)
    elif name == "get_relic_info":
        return _get_relic_info(**arguments)
    elif name == "get_coin_info":
        return _get_coin_info(**arguments)
    elif name == "analyze_roster":
        return _analyze_roster(**arguments)
    else:
        return f"未知工具: {name}"


# ═══════════════════ 工具实现 ═══════════════════

def _search_knowledge(query: str) -> str:
    """搜索界园肉鸽知识库."""
    results = rag.search(query, top_k=3)
    if not results:
        return "未找到相关知识。"
    lines = []
    for i, r in enumerate(results):
        lines.append(f"[{i+1}] {r['title']}\n{r['content'][:500]}")
    return "\n\n".join(lines)


def _get_operator_info(name: str) -> str:
    """查询干员详细信息."""
    op = data_loader.get_operator_by_name(name)
    if not op:
        # 模糊搜索
        data_loader._load()
        matches = [o for o in data_loader._operators if name.lower() in o["name"].lower()]
        if not matches:
            return f"未找到干员「{name}」。"
        ops_info = []
        for m in matches[:5]:
            ops_info.append(_format_operator(m))
        return "找到以下干员：\n\n" + "\n---\n".join(ops_info)
    return _format_operator(op)


def _get_relic_info(name: str) -> str:
    """查询藏品详细信息."""
    data_loader._load()
    matches = [r for r in data_loader._relics if name.lower() in r["name"].lower()]
    if not matches:
        return f"未找到藏品「{name}」。"
    lines = []
    for r in matches[:5]:
        lines.append(f"【{r['name']}】{r['rarity']}星\n效果：{r.get('effect', '暂无')}\n"
                     f"标签：{', '.join(r.get('tags', [])) or '无'}")
    return "\n\n".join(lines)


def _get_coin_info(name: str) -> str:
    """查询通宝详细信息."""
    data_loader._load()
    matches = [c for c in data_loader._coins if name.lower() in c["name"].lower()]
    if not matches:
        return f"未找到通宝「{name}」。"
    lines = []
    for c in matches[:5]:
        lines.append(f"【{c['name']}】{c['type']}\n效果：{c.get('effect', '暂无')}")
    return "\n\n".join(lines)


def _analyze_roster(theme: str = "界园", difficulty: str = "N0", floor: int = 1,
                    squad_id: str = "", style: str = "均衡流",
                    originium_ingot: int = 0, hope: int = 0, hp: int = 0,
                    shield: int = 0, tickets: int = 0,
                    operators: list[str] = None,
                    relics: list[str] = None,
                    coins: list[str] = None) -> str:
    """分析当前阵容优劣势."""
    operators = operators or []
    relics = relics or []
    coins = coins or []

    lines = [f"【阵容分析】主题={theme} 难度={difficulty} 第{floor}层"]
    lines.append(f"资源：源石锭{originium_ingot} 希望{hope} 生命{hp} 护盾{shield} 票券{tickets}")

    if operators:
        lines.append(f"\n已招募干员 {len(operators)} 名：")
        for op_name in operators:
            op = data_loader.get_operator_by_name(op_name)
            if op:
                lines.append(f"  - {op['name']} ({op['rarity']}★ {op.get('class','')}/{op.get('branch','')})")
    else:
        lines.append("\n暂无已招募干员信息")

    if relics:
        lines.append(f"\n持有藏品 {len(relics)} 件")
        for r_name in relics[:10]:
            relic = None
            data_loader._load()
            for r in data_loader._relics:
                if r["name"] == r_name:
                    relic = r
                    break
            if relic:
                lines.append(f"  - {relic['name']}（{relic.get('effect','')[:60]}）")

    if coins:
        lines.append(f"\n持有通宝 {len(coins)} 枚")
        for c_name in coins[:10]:
            data_loader._load()
            for c in data_loader._coins:
                if c["name"] == c_name:
                    lines.append(f"  - {c['name']} [{c['type']}]：{c.get('effect','')[:60]}")
                    break

    return "\n".join(lines)


# ═══════════════════ 工具定义（OpenAI function calling 格式） ═══════════════════

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "搜索界园肉鸽知识库，获取流程攻略、机制说明等知识。当用户问'怎么打''这关''机制''解锁'等问题时必须调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，如'第三层攻略''伺烛客机制''结局解锁条件'",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_operator_info",
            "description": "查询干员的详细信息，包括职业、分支、技能、天赋、肉鸽抓位评价。当用户问'xxx干员怎么样''xxx强不强''要不要抓xxx'时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "干员名称，如'丰川祥子''伊内丝'",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_relic_info",
            "description": "查询藏品详细信息，包括效果、稀有度、标签。当用户问'xxx藏品什么效果''xxx藏品强不强'时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "藏品名称",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_coin_info",
            "description": "查询通宝（钱币）详细信息，包括类型（衡钱/花钱/厉钱）和效果。当用户问'xxx通宝什么效果''xxx钱币怎么样'时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "通宝名称",
                    },
                },
                "required": ["name"],
            },
        },
    },
]


def _format_operator(op: dict) -> str:
    """格式化干员信息."""
    lines = [f"【{op['name']}】{op['rarity']}★ {op.get('class','')} / {op.get('branch','')}"]
    if op.get("tags"):
        lines.append(f"标签：{'、'.join(op['tags'])}")
    if op.get("skills"):
        skill_names = [s["name"] for s in op["skills"]]
        lines.append(f"技能：{' / '.join(skill_names)}")
    if op.get("talents"):
        for t in op["talents"][:2]:
            lines.append(f"天赋「{t['name']}」：{t.get('description','')[:100]}")
    return "\n".join(lines)
