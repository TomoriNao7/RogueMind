import { useState, useRef, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { analyzeStream } from '../api/client';

interface ChatMessage {
  role: 'user' | 'assistant' | 'status';
  content: string;
}

export default function Agent() {
  const gameState = useStore((s) => s.gameState);
  const sessionId = useStore((s) => s.sessionId);
  const llmConfigured = useStore((s) => s.llmConfigured);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const q = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: q }]);
    setLoading(true);

    try {
      const stream = analyzeStream(gameState, q, sessionId);
      let assistantContent = '';
      let statusMessages: string[] = [];

      // 先添加一个空的助手消息占位
      setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

      for await (const event of stream) {
        switch (event.type) {
          case 'status':
            // 工具调用状态
            statusMessages.push(event.content);
            setMessages((prev) => {
              const updated = [...prev];
              // 移除上一次的状态消息
              updated.filter(m => m.role === 'status').forEach(() => {
                const idx = updated.findIndex(m => m.role === 'status');
                if (idx >= 0) updated.splice(idx, 1);
              });
              // 添加当前所有状态
              const lastStatus = statusMessages[statusMessages.length - 1];
              if (lastStatus) {
                updated.push({ role: 'status', content: `🔍 ${lastStatus}` });
              }
              return updated;
            });
            break;

          case 'token':
            // 流式文本 — 打字机效果
            assistantContent += event.content;
            setMessages((prev) => {
              const updated = [...prev];
              // 清除状态消息
              const statusIdx = updated.findIndex(m => m.role === 'status');
              if (statusIdx >= 0) updated.splice(statusIdx, 1);
              // 更新最后一条助手消息
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
                updated[lastIdx] = { role: 'assistant', content: assistantContent };
              }
              return updated;
            });
            break;

          case 'error':
            setMessages((prev) => {
              const updated = [...prev];
              const statusIdx = updated.findIndex(m => m.role === 'status');
              if (statusIdx >= 0) updated.splice(statusIdx, 1);
              updated.push({ role: 'assistant', content: `❌ ${event.content}` });
              return updated;
            });
            break;

          case 'done':
            // 清理状态消息
            setMessages((prev) => prev.filter(m => m.role !== 'status'));
            break;
        }
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '请求失败';
      setMessages((prev) => [...prev, { role: 'assistant', content: `❌ ${msg}` }]);
    }

    setLoading(false);
    abortRef.current = null;
  };

  const clearChat = () => setMessages([]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 2 * var(--gap-lg))' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h1 style={{ color: 'var(--accent)' }}>Agent 分析</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-ghost" onClick={clearChat} disabled={loading}>清空对话</button>
          {loading && (
            <button className="btn btn-ghost" onClick={() => abortRef.current?.abort()}
              style={{ color: 'var(--text-muted)' }}>
              停止
            </button>
          )}
        </div>
      </div>

      {!llmConfigured && (
        <div className="card" style={{ marginBottom: 16, color: 'var(--text-muted)' }}>
          请先在「设置」中配置 LLM API Key
        </div>
      )}

      <div style={{
        flex: 1, overflow: 'auto', padding: 'var(--gap-md)',
        background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-primary)', marginBottom: 16,
      }}>
        {messages.length === 0 && (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: 60 }}>
            <p style={{ marginBottom: 8 }}>输入你的问题开始对话</p>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
              试试：「我的阵容需要补什么」「丰川祥子怎么样」「第三层应该注意什么」
            </p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{
            marginBottom: m.role === 'status' ? 4 : 12,
            padding: m.role === 'status' ? '4px 12px' : '8px 12px',
            borderRadius: 'var(--radius-sm)',
            background: m.role === 'user' ? 'var(--bg-tertiary)'
              : m.role === 'status' ? 'transparent' : 'transparent',
            border: m.role === 'assistant' ? '1px solid var(--border-primary)'
              : m.role === 'status' ? 'none' : 'none',
            maxWidth: m.role === 'status' ? '100%' : '90%',
            marginLeft: m.role === 'user' ? 'auto' : 0,
          }}>
            {m.role === 'status' ? (
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                {m.content}
              </span>
            ) : (
              <>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 4 }}>
                  {m.role === 'user' ? '你' : 'RogueMind'}
                </div>
                <div style={{ fontSize: 'var(--text-sm)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                  {m.content}
                  {loading && i === messages.length - 1 && m.role === 'assistant' && (
                    <span className="status-dot loading" style={{ display: 'inline-block', marginLeft: 2, verticalAlign: 'middle' }} />
                  )}
                </div>
              </>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <input value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="输入你的问题... (Enter 发送)"
          disabled={loading}
          style={{
            flex: 1, background: 'var(--bg-tertiary)', border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)',
            padding: '10px 12px', fontFamily: 'var(--font-sans)', fontSize: 'var(--text-sm)',
            outline: 'none',
          }} />
        <button className="btn" onClick={send} disabled={loading || !llmConfigured}
          style={{ minWidth: 80 }}>
          {loading ? '思考中' : '发送'}
        </button>
      </div>
    </div>
  );
}
