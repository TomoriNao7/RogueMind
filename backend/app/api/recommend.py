"""策略推荐 API 路由 — 招募/精二/藏品/路线/钱币推荐."""

from fastapi import APIRouter

from ..core import rule_engine
from ..models.schemas import GameState, RecommendResult

router = APIRouter(prefix="/api/recommend", tags=["recommend"])


@router.post("/recruit", response_model=RecommendResult)
async def recruit_recommend(state: GameState):
    """推荐下一步招募的干员."""
    return rule_engine.recommend_recruit(state)


@router.post("/promote", response_model=RecommendResult)
async def promote_recommend(state: GameState):
    """推荐最值得精二的干员."""
    return rule_engine.recommend_promote(state)


@router.post("/relic", response_model=RecommendResult)
async def relic_recommend(state: GameState):
    """推荐藏品：基于阵容缺口和资源匹配藏品标签."""
    return rule_engine.recommend_relic(state)


@router.post("/coin", response_model=RecommendResult)
async def coin_recommend(state: GameState):
    """推荐通宝：评价已持有通宝，推荐必拿通宝."""
    return rule_engine.recommend_coin(state)
