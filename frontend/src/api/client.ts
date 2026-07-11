// API 客户端 — 封装所有后端接口调用

const BASE = '';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err);
  }
  return res.json();
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error: { code: string; message: string } | null;
}

// 健康检查
export const healthCheck = () =>
  request<ApiResponse<{ status: string; version: string; rag_ready: boolean }>>('/api/health');

// 知识检索
export const searchKnowledge = (q: string, limit = 5) =>
  request<ApiResponse<{ results: { id: string; title: string; content: string; score: number }[] }>>(
    `/api/knowledge/search?q=${encodeURIComponent(q)}&limit=${limit}`
  );

// 钱盒容量计算
export const getCoinboxCapacity = (difficulty: string, squadId: string) =>
  request<ApiResponse<{ capacity: number; base: number; breakdown: string }>>(
    `/api/knowledge/coinbox-capacity?difficulty=${difficulty}&squad_id=${squadId}`
  );

// 统一名称搜索
export const searchAll = (q: string) =>
  request<ApiResponse<{
    operators: { id: string; name: string; rarity: number; class: string }[];
    relics: { id: string; name: string; effect: string }[];
    coins: { id: string; name: string; type: string; effect: string }[];
  }>>(`/api/knowledge/search-all?q=${encodeURIComponent(q)}`);

// 招募推荐
export const recommendRecruit = (state: unknown) =>
  request<{ type: string; recommendations: { rank: number; id: string; name: string; reason: string; score: number }[]; analysis: string; source: string }>(
    '/api/recommend/recruit', { method: 'POST', body: JSON.stringify(state) }
  );

// 精二推荐
export const recommendPromote = (state: unknown) =>
  request<{ type: string; recommendations: { rank: number; id: string; name: string; reason: string; score: number }[]; analysis: string; source: string }>(
    '/api/recommend/promote', { method: 'POST', body: JSON.stringify(state) }
  );

// 藏品推荐
export const recommendRelic = (state: unknown) =>
  request<{ type: string; recommendations: { rank: number; id: string; name: string; reason: string; score: number }[]; analysis: string; source: string }>(
    '/api/recommend/relic', { method: 'POST', body: JSON.stringify(state) }
  );

// 通宝推荐
export const recommendCoin = (state: unknown) =>
  request<{ type: string; recommendations: { rank: number; id: string; name: string; reason: string; score: number }[]; analysis: string; source: string }>(
    '/api/recommend/coin', { method: 'POST', body: JSON.stringify(state) }
  );

// Agent 分析（流式 SSE）
export async function* analyzeStream(state: unknown, question = '', sessionId = '') {
  const res = await fetch(`${BASE}/api/analyze/stream?question=${encodeURIComponent(question)}&session_id=${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(state),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(err);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error('不支持流式响应');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          yield data as { type: 'status' | 'token' | 'done' | 'error'; content: string };
        } catch {
          // 忽略解析失败的行
        }
      }
    }
  }
}

// 会话
export const createSession = () =>
  request<ApiResponse<{ session_id: string }>>('/api/session/create', { method: 'POST' });

export const endSession = (sessionId: string) =>
  request<ApiResponse<{ message: string }>>(`/api/session/${sessionId}/end`, { method: 'POST' });

// 设置
export const getModels = () =>
  request<ApiResponse<{ presets: { id: string; name: string; base_url: string; models: string[] }[] }>>('/api/settings/models');

export const getLLMConfig = () =>
  request<ApiResponse<{ config: { provider: string; base_url: string; api_key: string; model_name: string }; configured: boolean }>>('/api/settings/llm');

export const setLLMConfig = (config: { provider: string; base_url: string; api_key: string; model_name: string }) =>
  request<ApiResponse<{ message: string; configured: boolean }>>('/api/settings/llm', {
    method: 'POST', body: JSON.stringify(config),
  });
