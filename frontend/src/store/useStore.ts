// 全局状态管理 — Zustand

import { create } from 'zustand';

export interface PlayerOperator {
  operator_id: string;
  elite: number;
  level: number;
  potential: number;
  skill_level: number;
  skill_mastery: Record<string, number>;
  is_candle_holder: boolean;
  is_scrolled: boolean;
}

export interface Resources {
  originium_ingot: number;
  hope: number;
  hp: number;
  shield: number;
  tickets: number;
}

export interface GameState {
  theme: string;
  floor: number;
  style: string;
  difficulty: string;
  squad_id: string;
  operators: PlayerOperator[];
  relics: string[];
  resources: Resources;
  coinbox: { coins: string[]; capacity: number } | null;
}

interface AppState {
  // 连接状态
  backendReady: boolean;
  // 会话
  sessionId: string;
  // 游戏状态
  gameState: GameState;
  // 推荐结果
  recruitResult: unknown | null;
  promoteResult: unknown | null;
  relicResult: unknown | null;
  coinResult: unknown | null;
  // Agent 对话
  agentMessages: { role: string; content: string }[];
  agentLoading: boolean;
  // 设置
  llmConfigured: boolean;
  // 名称缓存（ID → 名称映射，跨页面保持）
  nameCache: Record<string, string>;

  // Actions
  setBackendReady: (v: boolean) => void;
  setSessionId: (id: string) => void;
  updateGameState: (patch: Partial<GameState>) => void;
  cacheName: (id: string, name: string) => void;
  setRecruitResult: (r: unknown) => void;
  setPromoteResult: (r: unknown) => void;
  setRelicResult: (r: unknown) => void;
  setCoinResult: (r: unknown) => void;
  addAgentMessage: (m: { role: string; content: string }) => void;
  clearAgentMessages: () => void;
  setAgentLoading: (v: boolean) => void;
  setLLMConfigured: (v: boolean) => void;
}

export const useStore = create<AppState>((set) => ({
  backendReady: false,
  sessionId: '',
  gameState: {
    theme: '界园',
    floor: 1,
    style: '均衡流',
    difficulty: 'N0',
    squad_id: '',
    operators: [],
    relics: [],
    resources: { originium_ingot: 0, hope: 6, hp: 8, shield: 0, tickets: 0 },
    coinbox: { coins: [], capacity: 7 },
  },
  recruitResult: null,
  promoteResult: null,
  relicResult: null,
  coinResult: null,
  agentMessages: [],
  agentLoading: false,
  llmConfigured: false,
  nameCache: {},

  setBackendReady: (v) => set({ backendReady: v }),
  setSessionId: (id) => set({ sessionId: id }),
  updateGameState: (patch) =>
    set((s) => ({ gameState: { ...s.gameState, ...patch } })),
  cacheName: (id, name) =>
    set((s) => ({ nameCache: { ...s.nameCache, [id]: name } })),
  setRecruitResult: (r) => set({ recruitResult: r }),
  setPromoteResult: (r) => set({ promoteResult: r }),
  setRelicResult: (r) => set({ relicResult: r }),
  setCoinResult: (r) => set({ coinResult: r }),
  addAgentMessage: (m) =>
    set((s) => ({ agentMessages: [...s.agentMessages, m] })),
  clearAgentMessages: () => set({ agentMessages: [] }),
  setAgentLoading: (v) => set({ agentLoading: v }),
  setLLMConfigured: (v) => set({ llmConfigured: v }),
}));
