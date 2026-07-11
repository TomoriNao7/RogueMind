"""Agent 深度分析 API — 支持普通和流式两种模式."""

from fastapi import APIRouter, Body, Query
from fastapi.responses import StreamingResponse

from ..core import agent
from ..models.schemas import GameState, RecommendResult

router = APIRouter(prefix="/api", tags=["agent"])


@router.post("/analyze", response_model=RecommendResult)
async def analyze_state(
    state: GameState = Body(description="游戏状态"),
    question: str = Query(default="", description="具体问题"),
    session_id: str = Query(default="", description="会话 ID（多轮对话时传入）"),
):
    """Agent 深度分析：支持多轮对话上下文和工具调用（非流式）."""
    return agent.analyze(state, question, session_id)


@router.post("/analyze/stream")
async def analyze_stream(
    state: GameState = Body(description="游戏状态"),
    question: str = Query(default="", description="具体问题"),
    session_id: str = Query(default="", description="会话 ID"),
):
    """Agent 深度分析（流式 SSE）：逐字输出 + 工具调用状态提示."""
    return StreamingResponse(
        agent.analyze_stream(state, question, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
