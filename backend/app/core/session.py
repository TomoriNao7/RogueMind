"""会话管理 — Redis 为主存储，自动降级到 JSON 文件.

每个游戏对局 = 一个独立会话。
- 开始新对局 → create_session()
- Agent 对话 → add_message()
- 获取上下文 → get_context()（过长时自动压缩）
- 结束对局 → end_session()
"""

import json
import time
from pathlib import Path
from typing import Optional

try:
    import redis
    _redis_client = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)
    _redis_client.ping()
    _use_redis = True
except Exception:
    _redis_client = None
    _use_redis = False

# 文件降级存储路径
FILE_DIR = Path(__file__).parent.parent.parent / "data" / "sessions"
FILE_DIR.mkdir(parents=True, exist_ok=True)

# 配置
MAX_CONTEXT_MESSAGES = 20       # 超过此数量触发压缩
SUMMARY_TRIGGER = 15            # 超过后保留最近 N 条，其余压缩为摘要
SESSION_TTL = 259200            # 3 天未活动自动过期（秒）
CLEANUP_DAYS = 3                # 文件存储时，超过此天数未修改的会话将被清理


# ═══════════════════ 会话生命周期 ═══════════════════

def create_session(session_id: str) -> dict:
    """创建新会话，返回初始状态."""
    session = {
        "session_id": session_id,
        "created_at": time.time(),
        "messages": [],
        "summary": "",
        "game_state": {},
    }
    _save(session_id, session)
    return session


def end_session(session_id: str) -> None:
    """结束会话，清空所有上下文."""
    if _use_redis:
        _redis_client.delete(f"session:{session_id}")
        _redis_client.delete(f"session:{session_id}:messages")
    else:
        path = FILE_DIR / f"{session_id}.json"
        if path.exists():
            path.unlink()


def get_session(session_id: str) -> Optional[dict]:
    """获取会话数据."""
    return _load(session_id)


# ═══════════════════ 对话管理 ═══════════════════

def add_message(session_id: str, role: str, content: str) -> dict:
    """向会话添加一条消息（role: user / assistant / system）."""
    session = _load(session_id)
    if not session:
        session = create_session(session_id)

    session["messages"].append({
        "role": role,
        "content": content,
        "timestamp": time.time(),
    })

    # 检查是否需要压缩
    if len(session["messages"]) > MAX_CONTEXT_MESSAGES:
        session = _compress(session)

    _save(session_id, session)
    return session


def get_context(session_id: str) -> list[dict]:
    """获取压缩后的上下文（给 LLM 用的消息列表）.

    返回格式适配 OpenAI Chat API：
    [{"role": "system", "content": "..."},
     {"role": "user", "content": "..."},
     {"role": "assistant", "content": "..."}, ...]
    """
    session = _load(session_id)
    if not session:
        return []

    messages = []

    # 摘要作为 system 消息
    if session.get("summary"):
        messages.append({
            "role": "system",
            "content": f"【历史对话摘要】{session['summary']}",
        })

    # 最近的消息
    recent = session["messages"][-SUMMARY_TRIGGER:]
    for msg in recent:
        messages.append({
            "role": msg["role"],
            "content": msg["content"],
        })

    return messages


def update_game_state(session_id: str, game_state: dict) -> None:
    """更新会话关联的游戏状态."""
    session = _load(session_id)
    if session:
        session["game_state"] = game_state
        _save(session_id, session)


# ═══════════════════ 上下文压缩 ═══════════════════

def _compress(session: dict) -> dict:
    """压缩会话：将早期消息合并为摘要，保留最近对话.

    早期消息超过 SUMMARY_TRIGGER 条时，用文本拼接方式生成简单摘要。
    （后期可接入 LLM 做智能摘要）
    """
    old_msgs = session["messages"][:-SUMMARY_TRIGGER]
    recent = session["messages"][-SUMMARY_TRIGGER:]

    # 简单摘要：拼接旧消息的关键内容
    summary_parts = []
    for msg in old_msgs:
        role = msg["role"]
        text = msg["content"][:200]
        summary_parts.append(f"[{role}]: {text}")

    old_summary = session.get("summary", "")
    new_summary = old_summary + "\n---\n" + "\n".join(summary_parts)

    # 再次压缩摘要（保留末尾 3000 字符）
    if len(new_summary) > 3000:
        new_summary = "...(更早的对话已省略)\n" + new_summary[-3000:]

    session["summary"] = new_summary
    session["messages"] = recent

    return session


# ═══════════════════ 存储层 ═══════════════════

def _save(session_id: str, session: dict) -> None:
    """保存会话，每次保存时刷新 TTL."""
    session["last_activity"] = time.time()
    if _use_redis:
        key = f"session:{session_id}"
        _redis_client.set(key, json.dumps(session, ensure_ascii=False), ex=SESSION_TTL)
    else:
        path = FILE_DIR / f"{session_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2)


def cleanup_expired() -> int:
    """清理超过 3 天未活动的会话（仅文件存储模式生效，Redis 由 TTL 自动处理）.

    Returns:
        清理的会话数量
    """
    if _use_redis:
        return 0

    cleaned = 0
    cutoff = time.time() - CLEANUP_DAYS * 86400
    for path in FILE_DIR.glob("*.json"):
        if path.stat().st_mtime < cutoff:
            path.unlink()
            cleaned += 1
    return cleaned


def _load(session_id: str) -> Optional[dict]:
    """加载会话."""
    if _use_redis:
        data = _redis_client.get(f"session:{session_id}")
        return json.loads(data) if data else None
    else:
        path = FILE_DIR / f"{session_id}.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return None
