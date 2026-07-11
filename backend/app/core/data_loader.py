"""游戏数据加载模块 — 将 JSON 数据文件加载到内存并提供筛选查询."""

import sys
import json
from pathlib import Path
from typing import Optional

if getattr(sys, 'frozen', False):
    DATA_DIR = Path(sys._MEIPASS) / "data"
else:
    DATA_DIR = Path(__file__).parent.parent.parent / "data"

# 缓存：首次访问时加载，后续直接返回
_operators: list[dict] = []
_relics: list[dict] = []
_coins: list[dict] = []
_events: list[dict] = []
_squads: list[dict] = []
_loaded = False


def _load():
    """加载所有 JSON 数据文件到内存（仅首次调用时执行）."""
    global _operators, _relics, _coins, _events, _squads, _loaded
    if _loaded:
        return
    with open(DATA_DIR / "operators.json", encoding="utf-8") as f:
        _operators = json.load(f)
    with open(DATA_DIR / "relics.json", encoding="utf-8") as f:
        _relics = json.load(f)
    with open(DATA_DIR / "coins.json", encoding="utf-8") as f:
        _coins = json.load(f)
    with open(DATA_DIR / "events.json", encoding="utf-8") as f:
        _events = json.load(f)
    with open(DATA_DIR / "squads.json", encoding="utf-8") as f:
        _squads = json.load(f)
    _loaded = True


# ═══════════════════ 干员 ═══════════════════

def get_operators(
    rarity: Optional[int] = None,
    operator_class: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> list[dict]:
    """按稀有度、职业或标签筛选干员."""
    _load()
    result = _operators
    if rarity is not None:
        result = [o for o in result if o["rarity"] == rarity]
    if operator_class:
        result = [o for o in result if o["class"] == operator_class]
    if tags:
        result = [o for o in result if any(t in o.get("tags", []) for t in tags)]
    return result


def get_operator_by_id(operator_id: str) -> Optional[dict]:
    """通过 ID 查找干员."""
    _load()
    for o in _operators:
        if o["id"] == operator_id:
            return o
    return None


def get_operator_by_name(name: str) -> Optional[dict]:
    """通过名称查找干员."""
    _load()
    for o in _operators:
        if o["name"] == name:
            return o
    return None


# ═══════════════════ 藏品 ═══════════════════

def get_relics(
    rarity: Optional[int] = None,
    tags: Optional[list[str]] = None,
    theme: str = "界园",
) -> list[dict]:
    """按稀有度、标签或主题筛选藏品."""
    _load()
    result = [r for r in _relics if r.get("theme") == theme]
    if rarity is not None:
        result = [r for r in result if r["rarity"] == rarity]
    if tags:
        result = [r for r in result if any(t in r.get("tags", []) for t in tags)]
    return result


def get_relic_by_id(relic_id: str) -> Optional[dict]:
    """通过 ID 查找藏品."""
    _load()
    for r in _relics:
        if r["id"] == relic_id:
            return r
    return None


# ═══════════════════ 钱币 ═══════════════════

def get_coins(coin_type: Optional[str] = None) -> list[dict]:
    """按类型筛选钱币（衡钱/花钱/厉钱）."""
    _load()
    if coin_type:
        return [c for c in _coins if c["type"] == coin_type]
    return _coins


def get_coin_by_id(coin_id: str) -> Optional[dict]:
    """通过 ID 查找钱币."""
    _load()
    for c in _coins:
        if c["id"] == coin_id:
            return c
    return None


# ═══════════════════ 事件 ═══════════════════

def get_events(region: Optional[str] = None, node_type: Optional[str] = None) -> list[dict]:
    """按区域或节点类型筛选事件."""
    _load()
    result = _events
    if region:
        result = [e for e in result if e.get("region") == region]
    if node_type:
        result = [e for e in result if e.get("node_type") == node_type]
    return result


# ═══════════════════ 分队 ═══════════════════

def get_squads() -> list[dict]:
    """获取所有分队."""
    _load()
    return _squads


def get_squad_by_id(squad_id: str) -> Optional[dict]:
    """通过 ID 查找分队."""
    _load()
    for s in _squads:
        if s["id"] == squad_id:
            return s
    return None
