"""Agent 推理模块 — ReAct 循环 + 工具调用 + 流式输出."""

import json
from typing import AsyncGenerator

from openai import OpenAI

from . import rag, llm_config, session, tools
from ..models.schemas import GameState, RecommendResult, RecommendItem


# 最大 ReAct 循环次数（防止无限循环）
MAX_TOOL_ROUNDS = 5


# ═══════════════════ 非流式分析（保留向后兼容） ═══════════════════

def analyze(state: GameState, question: str = "", session_id: str = "") -> RecommendResult:
    """对当前游戏状态进行深度分析（非流式，保留兼容）."""
    if not llm_config.is_configured():
        return RecommendResult(
            type="analysis",
            recommendations=[],
            analysis="LLM 未配置，请在设置中填入 API Key 后使用 Agent 分析功能。",
            source="agent",
        )

    config = llm_config.load_config()
    client = OpenAI(base_url=config["base_url"], api_key=config["api_key"])

    # 创建或获取会话
    if session_id:
        session.update_game_state(session_id, state.model_dump())
        if question:
            session.add_message(session_id, "user", question)

    # RAG 预检索（作为初始上下文）
    rag_query = _build_rag_query(state, question or "")
    rag_results = rag.search(rag_query, top_k=3)

    # 构建消息
    messages = _build_messages(state, rag_results, question, session_id)

    try:
        # ReAct 循环
        for _ in range(MAX_TOOL_ROUNDS):
            response = client.chat.completions.create(
                model=config["model_name"],
                messages=messages,
                tools=tools.TOOLS,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1500,
            )

            msg = response.choices[0].message

            # 如果有工具调用
            if msg.tool_calls:
                messages.append(msg)  # 添加助手的工具调用消息

                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    result = tools.execute_tool(tool_name, args)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })

                continue  # 继续循环，让 LLM 基于工具结果回答

            # 没有工具调用，得到最终回复
            reply = msg.content.strip()
            break
        else:
            # 超过最大循环次数，强制要求总结
            reply = "抱歉，分析过程过于复杂。请尝试更具体地描述你的问题。"

    except Exception as e:
        return RecommendResult(
            type="analysis",
            recommendations=[],
            analysis=f"LLM 调用失败：{str(e)}",
            source="agent",
        )

    # 保存助手回复到会话
    if session_id and reply:
        session.add_message(session_id, "assistant", reply)

    return RecommendResult(
        type="analysis",
        recommendations=[],
        analysis=reply,
        source="agent",
    )


# ═══════════════════ 流式分析（SSE） ═══════════════════

async def analyze_stream(
    state: GameState,
    question: str = "",
    session_id: str = "",
) -> AsyncGenerator[str, None]:
    """流式 Agent 分析，通过 SSE 逐步返回结果.

    Yields:
        SSE 格式的事件字符串：
        - "data: {"type":"status","content":"..."}\n\n" — 状态更新（正在搜索、正在查询等）
        - "data: {"type":"token","content":"..."}\n\n" — 流式文本片段
        - "data: {"type":"done"}\n\n" — 完成信号
        - "data: {"type":"error","content":"..."}\n\n" — 错误
    """
    if not llm_config.is_configured():
        yield _sse("error", "LLM 未配置，请在设置中填入 API Key。")
        return

    config = llm_config.load_config()
    client = OpenAI(base_url=config["base_url"], api_key=config["api_key"])

    # 创建或获取会话
    if session_id:
        session.update_game_state(session_id, state.model_dump())
        if question:
            session.add_message(session_id, "user", question)

    # RAG 预检索
    yield _sse("status", "正在搜索知识库...")
    rag_query = _build_rag_query(state, question or "")
    rag_results = rag.search(rag_query, top_k=3)

    # 构建消息
    messages = _build_messages(state, rag_results, question, session_id)

    full_reply = ""

    try:
        # ReAct 循环
        for round_num in range(MAX_TOOL_ROUNDS):
            response = client.chat.completions.create(
                model=config["model_name"],
                messages=messages,
                tools=tools.TOOLS,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1500,
            )

            msg = response.choices[0].message

            # 如果有工具调用
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    tool_labels = {
                        "search_knowledge": "搜索知识库",
                        "get_operator_info": "查询干员数据",
                        "get_relic_info": "查询藏品数据",
                        "get_coin_info": "查询通宝数据",
                    }
                    label = tool_labels.get(tool_name, f"调用 {tool_name}")
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    arg_preview = list(args.values())[0] if args else ""
                    yield _sse("status", f"{label}：{arg_preview}")

                messages.append(msg)

                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    result = tools.execute_tool(tool_name, args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })

                continue  # 继续循环

            # 没有工具调用——流式输出最终回复
            yield _sse("status", "正在生成回复...")
            break
        else:
            full_reply = "抱歉，分析过程过于复杂。请尝试更具体地描述你的问题。"
            yield _sse("token", full_reply)
            yield _sse("done", "")
            if session_id:
                session.add_message(session_id, "assistant", full_reply)
            return

        # 流式输出最终回复
        stream = client.chat.completions.create(
            model=config["model_name"],
            messages=messages,
            temperature=0.7,
            max_tokens=1500,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                full_reply += delta.content
                yield _sse("token", delta.content)

        yield _sse("done", "")

    except Exception as e:
        yield _sse("error", f"LLM 调用失败：{str(e)}")

    # 保存助手回复到会话
    if session_id and full_reply:
        session.add_message(session_id, "assistant", full_reply)


# ═══════════════════ 辅助函数 ═══════════════════

def _sse(event_type: str, content: str) -> str:
    """构建 SSE 事件字符串."""
    data = json.dumps({"type": event_type, "content": content}, ensure_ascii=False)
    return f"data: {data}\n\n"


def _build_messages(
    state: GameState,
    rag_results: list[dict],
    question: str,
    session_id: str,
) -> list[dict]:
    """构建完整消息列表."""
    system_prompt = _build_system_prompt(state, rag_results)

    messages = [{"role": "system", "content": system_prompt}]

    if session_id:
        history = session.get_context(session_id)
        messages = [{"role": "system", "content": system_prompt}] + history[-10:]

    if not question:
        question = "请分析我当前的阵容和状态，给出下一步的行动建议。"
    messages.append({"role": "user", "content": question})

    return messages


def _build_system_prompt(state: GameState, rag_results: list[dict] = None) -> str:
    """构建系统提示词."""
    rag_results = rag_results or []

    state_lines = [
        "你是明日方舟集成战略（肉鸽）界园主题的策略分析师。",
        "",
        "【能力说明】",
        "你可以使用以下工具来获取信息：",
        "- search_knowledge：搜索界园流程攻略、机制说明",
        "- get_operator_info：查询干员详细信息",
        "- get_relic_info：查询藏品效果",
        "- get_coin_info：查询通宝效果",
        "当用户问到你不知道的信息时，务必先调用工具查询，再基于查询结果回答。",
        "",
        "【当前游戏状态】",
        f"- 主题：{state.theme}，第{state.floor}层，难度{state.difficulty}",
        f"- 行动风格：{state.style.value}",
        f"- 资源：源石锭{state.resources.originium_ingot}，希望{state.resources.hope}，"
        f"生命{state.resources.hp}，护盾{state.resources.shield}，票券{state.resources.tickets}",
    ]

    if state.operators:
        from .data_loader import get_operator_by_id
        state_lines.append(f"\n【已招募干员】({len(state.operators)}名)")
        for po in state.operators:
            op = get_operator_by_id(po.operator_id)
            if op:
                e = f"精{po.elite}"
                extra = " [伺烛客]" if po.is_candle_holder else ""
                state_lines.append(f"  - {op['name']} {op['rarity']}★ {op['class']}/{op['branch']} {e} Lv{po.level}{extra}")

    if state.relics:
        from .data_loader import get_relic_by_id
        state_lines.append(f"\n【持有藏品】({len(state.relics)}件)")
        for rid in state.relics[:8]:
            r = get_relic_by_id(rid)
            if r:
                state_lines.append(f"  - {r['name']}（{r.get('effect', '')[:50]}）")

    state_text = "\n".join(state_lines)

    rag_text = ""
    if rag_results:
        rag_text = "\n【知识库参考】\n" + "\n".join(
            f"- {d['title']}: {d['content'][:300]}" for d in rag_results
        )

    return f"""{state_text}

{rag_text}

【分析要求】
1. 评估当前阵容的优劣势
2. 结合当前层数和资源，给出下一步行动建议
3. 如果用户询问具体干员/藏品/通宝，务必先调用工具查询再回答
4. 考虑行动风格（{state.style.value}）给出针对性策略

请用简洁清晰的中文回复，分点列出建议。"""


def _build_rag_query(state: GameState, question: str) -> str:
    """根据游戏状态构建 RAG 检索查询."""
    parts = [f"界园第{state.floor}层", f"难度{state.difficulty}"]

    if state.operators:
        from .data_loader import get_operator_by_id
        names = []
        for po in state.operators[:5]:
            op = get_operator_by_id(po.operator_id)
            if op:
                names.append(op["name"])
        parts.append(f"已招募: {', '.join(names)}")

    if question:
        parts.append(question)

    return " ".join(parts)
