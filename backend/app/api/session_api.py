"""会话管理 API."""

import uuid

from fastapi import APIRouter

from ..core import session

router = APIRouter(prefix="/api/session", tags=["session"])


@router.post("/create")
async def create_session():
    """创建新的游戏会话，返回 session_id."""
    sid = uuid.uuid4().hex[:12]
    session.create_session(sid)
    return {
        "success": True,
        "data": {"session_id": sid},
        "error": None,
    }


@router.post("/{session_id}/end")
async def end_session(session_id: str):
    """结束当前会话，清空所有上下文."""
    session.end_session(session_id)
    return {
        "success": True,
        "data": {"message": "会话已结束，上下文已清空"},
        "error": None,
    }


@router.get("/{session_id}")
async def get_session(session_id: str):
    """获取会话信息."""
    s = session.get_session(session_id)
    if not s:
        return {
            "success": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "会话不存在或已过期"},
        }
    return {
        "success": True,
        "data": {
            "session_id": s["session_id"],
            "message_count": len(s.get("messages", [])),
            "has_summary": bool(s.get("summary")),
            "created_at": s.get("created_at"),
        },
        "error": None,
    }
