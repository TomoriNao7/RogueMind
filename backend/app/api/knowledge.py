"""知识检索 API 路由."""

from fastapi import APIRouter, Query

from ..core import rag, data_loader

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/search-all")
async def search_all(q: str = Query(default="", description="名称搜索"), limit: int = Query(default=10)):
    """统一名称搜索：同时搜索干员、藏品、通宝."""
    data_loader._load()

    operators = []
    relics = []
    coins = []

    if q:
        q_lower = q.lower()
        for o in data_loader._operators:
            if q_lower in o["name"].lower():
                operators.append({"id": o["id"], "name": o["name"], "rarity": o["rarity"], "class": o.get("class", "")})
        for r in data_loader._relics:
            if q_lower in r["name"].lower():
                relics.append({"id": r["id"], "name": r["name"], "effect": r.get("effect", "")[:60]})
        for c in data_loader._coins:
            if q_lower in c["name"].lower():
                coins.append({"id": c["id"], "name": c["name"], "type": c["type"], "effect": c.get("effect", "")})

    return {
        "success": True,
        "data": {
            "operators": operators[:limit],
            "relics": relics[:limit],
            "coins": coins[:limit],
        },
        "error": None,
    }


@router.get("/search")
async def search_knowledge(
    q: str = Query(description="搜索关键词"),
    limit: int = Query(default=5, ge=1, le=20),
):
    """混合检索知识库（BM25 + 向量 + RRF 融合）."""
    results = rag.search(q, top_k=limit)
    return {
        "success": True,
        "data": {
            "results": results,
            "query": q,
            "total": len(results),
        },
        "error": None,
    }


@router.get("/operators")
async def search_operators(
    q: str = Query(default="", description="名称搜索"),
    rarity: int = Query(default=None, description="稀有度筛选"),
    operator_class: str = Query(default=None, description="职业筛选"),
):
    """精确查询干员数据."""
    data_loader._load()
    operators = data_loader._operators

    if q:
        operators = [o for o in operators if q in o["name"]]
    if rarity:
        operators = [o for o in operators if o["rarity"] == rarity]
    if operator_class:
        operators = [o for o in operators if o["class"] == operator_class]

    return {
        "success": True,
        "data": {"operators": operators[:20], "total": len(operators)},
        "error": None,
    }


@router.get("/relics")
async def search_relics(
    q: str = Query(default="", description="名称/效果搜索"),
    rarity: int = Query(default=None, description="稀有度筛选"),
):
    """精确查询藏品数据."""
    data_loader._load()
    relics = data_loader._relics

    if q:
        relics = [r for r in relics if q in r["name"] or q in r.get("effect", "")]
    if rarity:
        relics = [r for r in relics if r["rarity"] == rarity]

    return {
        "success": True,
        "data": {"relics": relics[:20], "total": len(relics)},
        "error": None,
    }


@router.get("/coins")
async def search_coins(
    coin_type: str = Query(default=None, description="钱币类型：衡钱/花钱/厉钱"),
):
    """查询钱币数据."""
    coins = data_loader.get_coins(coin_type)
    return {
        "success": True,
        "data": {"coins": coins, "total": len(coins)},
        "error": None,
    }


@router.get("/coinbox-capacity")
async def coinbox_capacity(
    difficulty: str = Query(default="N0", description="难度等级"),
    squad_id: str = Query(default="", description="分队 ID"),
):
    """计算钱盒容量：基础 7，N3+ +3，游客分队 +1."""
    base = 7

    # 解析难度数字
    diff_num = 0
    if difficulty.startswith("N"):
        try:
            diff_num = int(difficulty[1:])
        except ValueError:
            diff_num = 0

    # N3+: 容量 +3（7→10）
    if diff_num >= 3:
        base += 3

    # 游客分队: +1（古今学识解锁后+2，当前默认+1）
    if squad_id == "squad_jy_003":
        base += 1

    return {
        "success": True,
        "data": {
            "capacity": base,
            "base": 7,
            "breakdown": f"基础7{' + N3+扩容3' if diff_num >= 3 else ''}{' + 游客分队1' if squad_id == 'squad_jy_003' else ''}",
        },
        "error": None,
    }


@router.get("/status")
async def rag_status():
    """RAG 系统状态查询."""
    return {
        "success": True,
        "data": {
            "rag_ready": rag.is_ready(),
            "doc_count": len(rag._bm25_docs),
        },
        "error": None,
    }
