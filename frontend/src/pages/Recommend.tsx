import { useState } from 'react';
import { useStore } from '../store/useStore';
import { recommendRecruit, recommendPromote, recommendRelic, recommendCoin } from '../api/client';

type Tab = 'recruit' | 'promote' | 'relic' | 'coin';

const TABS: { key: Tab; label: string }[] = [
  { key: 'recruit', label: '招募推荐' },
  { key: 'promote', label: '精二推荐' },
  { key: 'relic', label: '藏品推荐' },
  { key: 'coin', label: '通宝推荐' },
];

export default function Recommend() {
  const gameState = useStore((s) => s.gameState);
  const [tab, setTab] = useState<Tab>('recruit');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    type: string;
    recommendations: { rank: number; id: string; name: string; reason: string; score: number }[];
    analysis: string;
    source: string;
  } | null>(null);
  const [error, setError] = useState('');

  const fetchRecommend = async () => {
    setLoading(true);
    setError('');
    try {
      const api = { recruit: recommendRecruit, promote: recommendPromote, relic: recommendRelic, coin: recommendCoin }[tab];
      const r = await api(gameState);
      setResult(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '请求失败');
    }
    setLoading(false);
  };

  return (
    <div>
      <h1 style={{ color: 'var(--accent)', marginBottom: 24 }}>策略推荐</h1>

      {/* Tab 切换 */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16 }}>
        {TABS.map((t) => (
          <button key={t.key} onClick={() => { setTab(t.key); setResult(null); }}
            style={{
              padding: '8px 20px',
              border: `1px solid ${tab === t.key ? 'var(--accent)' : 'var(--border-primary)'}`,
              borderRadius: 'var(--radius-sm)',
              background: tab === t.key ? 'var(--bg-tertiary)' : 'transparent',
              color: tab === t.key ? 'var(--accent)' : 'var(--text-secondary)',
              cursor: 'pointer', fontFamily: 'var(--font-sans)', fontSize: 'var(--text-sm)',
            }}>
            {t.label}
          </button>
        ))}
      </div>

      <button className="btn" onClick={fetchRecommend} disabled={loading}
        style={{ marginBottom: 16 }}>
        {loading ? '分析中...' : '获取推荐'}
      </button>

      {error && <div className="card" style={{ color: 'var(--text-muted)', marginBottom: 16 }}>{error}</div>}

      {result && (
        <div className="card" style={{ marginBottom: 16 }}>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 16, lineHeight: 1.6 }}>
            {result.analysis}
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {result.recommendations.map((r) => (
              <div key={r.rank} style={{
                background: 'var(--bg-tertiary)',
                border: `1px solid ${r.rank <= 2 ? 'var(--border-accent)' : 'var(--border-primary)'}`,
                borderRadius: 'var(--radius-sm)',
                padding: 12,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 500 }}>
                    #{r.rank} {r.name}
                  </span>
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                    评分 {r.score}
                  </span>
                </div>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  {r.reason}
                </p>
              </div>
            ))}
          </div>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 12 }}>
            来源：{result.source === 'rule_engine' ? '规则引擎' : 'AI 分析'}
          </p>
        </div>
      )}
    </div>
  );
}
