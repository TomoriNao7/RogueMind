import { useState, useCallback, useRef, useEffect } from 'react';
import { useStore, type PlayerOperator } from '../store/useStore';
import { searchAll, getCoinboxCapacity } from '../api/client';

interface SearchResult {
  id: string; name: string; rarity?: number; class?: string;
  type?: string; effect?: string;
}

export default function StateInput() {
  const gameState = useStore((s) => s.gameState);
  const update = useStore((s) => s.updateGameState);
  const nameCache = useStore((s) => s.nameCache);
  const cacheNameStore = useStore((s) => s.cacheName);

  const cacheName = (id: string, name: string) => cacheNameStore(id, name);
  const getName = (id: string) => nameCache[id] || id;

  // 难度或分队变化时自动计算钱盒容量
  useEffect(() => {
    getCoinboxCapacity(gameState.difficulty, gameState.squad_id).then((r) => {
      const cap = r.data.capacity;
      const cb = gameState.coinbox || { coins: [], capacity: cap };
      update({ coinbox: { ...cb, capacity: cap } });
    }).catch(() => {});
  }, [gameState.difficulty, gameState.squad_id]);

  return (
    <div>
      <h1 style={{ color: 'var(--accent)', marginBottom: 24 }}>游戏状态</h1>

      {/* 基础设置 */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h2 style={{ marginBottom: 12 }}>基础设置</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--gap-md)' }}>
          <Field label="主题">
            <select value={gameState.theme} onChange={(e) => update({ theme: e.target.value })} style={sSelect}>
              <option>界园</option>
            </select>
          </Field>
          <Field label="层数">
            <select value={gameState.floor} onChange={(e) => update({ floor: +e.target.value })} style={sSelect}>
              {[1,2,3,4,5,6].map((n) => <option key={n} value={n}>第 {n} 层</option>)}
            </select>
          </Field>
          <Field label="难度">
            <select value={gameState.difficulty} onChange={(e) => update({ difficulty: e.target.value })} style={sSelect}>
              {Array.from({ length: 19 }, (_, i) => (
                <option key={i}>{i === 0 ? 'N0' : `N${i}`}</option>
              ))}
            </select>
          </Field>
          <Field label="分队">
            <select value={gameState.squad_id} onChange={(e) => update({ squad_id: e.target.value })} style={sSelect}>
              <option value="">未选择</option>
              {[
                ['squad_jy_006','指挥分队'],['squad_jy_007','特勤分队'],['squad_jy_008','后勤分队'],
                ['squad_jy_009','突击战术分队'],['squad_jy_010','堡垒战术分队'],['squad_jy_011','远程战术分队'],
                ['squad_jy_012','破坏战术分队'],['squad_jy_013','高规格分队'],
              ].map(([id, name]) => <option key={id} value={id}>{name}</option>)}
            </select>
          </Field>
          <Field label="行动风格">
            <select value={gameState.style} onChange={(e) => update({ style: e.target.value })} style={sSelect}>
              {['均衡流','发育流','电表倒转','速通流'].map((s) => <option key={s}>{s}</option>)}
            </select>
          </Field>
        </div>
      </div>

      {/* 资源 */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h2 style={{ marginBottom: 12 }}>资源</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr', gap: 'var(--gap-md)' }}>
          {([
            { key: 'originium_ingot' as const, label: '源石锭', minV: 0, maxV: 99 },
            { key: 'hope' as const, label: '希望', minV: 0, maxV: 20 },
            { key: 'hp' as const, label: '生命值', minV: 0, maxV: 20 },
            { key: 'shield' as const, label: '护盾', minV: 0, maxV: 10 },
            { key: 'tickets' as const, label: '票券', minV: 0, maxV: 20 },
          ]).map(({key, label, minV, maxV}) => (
            <Field key={key} label={label}>
              <input type="number" value={gameState.resources[key]}
                min={minV} max={maxV}
                onChange={(e) => update({ resources: { ...gameState.resources, [key]: +e.target.value } })}
                style={sInput} />
            </Field>
          ))}
        </div>
      </div>

      {/* 干员 — 名称搜索 */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h2 style={{ marginBottom: 12 }}>已招募干员 ({gameState.operators.length})</h2>
        <NameSearch
          placeholder="搜索干员名称..."
          onPick={(r) => {
            cacheName(r.id, r.name);
            const op: PlayerOperator = {
              operator_id: r.id, elite: 1, level: 1, potential: 1,
              skill_level: 7, skill_mastery: { '1': 0, '2': 0, '3': 0 },
              is_candle_holder: false, is_scrolled: false,
            };
            update({ operators: [...gameState.operators, op] });
          }}
          filter="operator"
        />
        <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {gameState.operators.map((op, i) => (
            <OpTag key={i} op={op} name={getName(op.operator_id)}
              onElite={(v) => {
                const ops = [...gameState.operators];
                ops[i] = { ...ops[i], elite: v };
                update({ operators: ops });
              }}
              onLevel={(v) => {
                const ops = [...gameState.operators];
                ops[i] = { ...ops[i], level: v };
                update({ operators: ops });
              }}
              onCandle={() => {
                const ops = [...gameState.operators];
                ops[i] = { ...ops[i], is_candle_holder: !ops[i].is_candle_holder };
                update({ operators: ops });
              }}
              onRemove={() => {
                update({ operators: gameState.operators.filter((_, j) => j !== i) });
              }}
            />
          ))}
        </div>
      </div>

      {/* 藏品 — 名称搜索 */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h2 style={{ marginBottom: 12 }}>藏品 ({gameState.relics.length})</h2>
        <NameSearch
          placeholder="搜索藏品名称..."
          onPick={(r) => { cacheName(r.id, r.name); update({ relics: [...gameState.relics, r.id] }); }}
          filter="relic"
        />
        <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {gameState.relics.map((rid, i) => (
            <span key={i} onClick={() => update({ relics: gameState.relics.filter((_, j) => j !== i) })}
              style={{ background:'var(--bg-tertiary)',border:'1px solid var(--border-primary)',
                borderRadius:'var(--radius-sm)',padding:'4px 8px',fontSize:'var(--text-xs)',cursor:'pointer' }}>
              {getName(rid)} ×
            </span>
          ))}
        </div>
      </div>

      {/* 通宝 — 名称搜索 */}
      <div className="card">
        <h2 style={{ marginBottom: 12 }}>
          通宝 ({gameState.coinbox?.coins?.length || 0}/{gameState.coinbox?.capacity || 7})
        </h2>
        <NameSearch
          placeholder="搜索通宝名称..."
          onPick={(r) => {
            cacheName(r.id, r.name);
            const cb = gameState.coinbox || { coins: [], capacity: 7 };
            update({ coinbox: { ...cb, coins: [...cb.coins, r.id] } });
          }}
          filter="coin"
        />
        <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {(gameState.coinbox?.coins || []).map((cid, i) => (
            <span key={i} onClick={() => {
              const cb = gameState.coinbox!;
              update({ coinbox: { ...cb, coins: cb.coins.filter((_, j) => j !== i) } });
            }}
              style={{ background:'var(--bg-tertiary)',border:'1px solid var(--border-primary)',
                borderRadius:'var(--radius-sm)',padding:'4px 8px',fontSize:'var(--text-xs)',cursor:'pointer' }}>
              {getName(cid)} ×
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════ 名称搜索组件 ═══════════════════

function NameSearch({ placeholder, onPick, filter }: {
  placeholder: string;
  onPick: (r: SearchResult) => void;
  filter: 'operator' | 'relic' | 'coin';
}) {
  const [q, setQ] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const doSearch = useCallback((val: string) => {
    setQ(val);
    if (timerRef.current) clearTimeout(timerRef.current);
    if (!val.trim()) { setResults([]); setOpen(false); return; }
    timerRef.current = setTimeout(async () => {
      try {
        const r = await searchAll(val);
        const items: SearchResult[] = [];
        if (filter === 'operator') items.push(...r.data.operators);
        if (filter === 'relic') items.push(...r.data.relics);
        if (filter === 'coin') items.push(...r.data.coins);
        setResults(items.slice(0, 8));
        setOpen(true);
      } catch { setResults([]); }
    }, 200);
  }, [filter]);

  return (
    <div style={{ position: 'relative' }}>
      <input value={q} onChange={(e) => doSearch(e.target.value)}
        onFocus={() => results.length > 0 && setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder={placeholder}
        style={{
          ...sInput, width: '100%', maxWidth: 400,
        }} />
      {open && results.length > 0 && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, zIndex: 10,
          background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)',
          borderRadius: 'var(--radius-sm)', width: 400, maxHeight: 300, overflow: 'auto',
        }}>
          {results.map((r) => (
            <div key={r.id} onMouseDown={() => { onPick(r); setQ(''); setOpen(false); }}
              style={{
                padding: '8px 12px', cursor: 'pointer',
                borderBottom: '1px solid var(--border-primary)',
                fontSize: 'var(--text-sm)',
              }}>
              <span style={{ color: 'var(--text-primary)' }}>{r.name}</span>
              {r.rarity !== undefined && (
                <span style={{ color: 'var(--text-muted)', marginLeft: 8 }}>{r.rarity}★ {r.class}</span>
              )}
              {r.type && (
                <span style={{ color: 'var(--text-muted)', marginLeft: 8 }}>[{r.type}]</span>
              )}
              {r.effect && (
                <span style={{ color: 'var(--text-muted)', marginLeft: 8, fontSize: 'var(--text-xs)' }}>
                  {r.effect.slice(0, 40)}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ═══════════════════ 干员标签组件 ═══════════════════

function OpTag({ op, name, onElite, onLevel, onCandle, onRemove }: {
  op: PlayerOperator; name: string;
  onElite: (v: number) => void;
  onLevel: (v: number) => void;
  onCandle: () => void;
  onRemove: () => void;
}) {
  return (
    <div style={{
      background: 'var(--bg-tertiary)', border: '1px solid var(--border-primary)',
      borderRadius: 'var(--radius-sm)', padding: '8px 12px',
      display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--text-sm)',
    }}>
      <span style={{ fontWeight: 500 }}>{name}</span>
      <select value={op.elite} onChange={(e) => onElite(+e.target.value)}
        style={{ ...sSelect, width: 56, padding: '2px 4px', fontSize: 'var(--text-xs)' }}>
        <option value={0}>精0</option><option value={1}>精1</option><option value={2}>精2</option>
      </select>
      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Lv</span>
      <input type="number" value={op.level} min={1} max={90}
        style={{ ...sInput, width: 48, padding: '2px 4px', fontSize: 'var(--text-xs)' }}
        onChange={(e) => onLevel(+e.target.value)} />
      <button onClick={onCandle}
        title={op.is_candle_holder ? '已燃烛（可进入岁兽残识）' : '未燃烛（点击燃烛成为伺烛客）'}
        style={{
          background: op.is_candle_holder ? 'var(--border-accent)' : 'transparent',
          border: `1px solid ${op.is_candle_holder ? 'var(--accent)' : 'var(--border-primary)'}`,
          borderRadius: 'var(--radius-sm)',
          color: op.is_candle_holder ? 'var(--bg-primary)' : 'var(--text-muted)',
          fontSize: 'var(--text-xs)', cursor: 'pointer', padding: '2px 6px',
          fontWeight: op.is_candle_holder ? 500 : 400,
        }}>
        {op.is_candle_holder ? '伺烛' : '燃烛'}
      </button>
      <button onClick={onRemove}
        style={{ background:'none',border:'none',color:'var(--text-muted)',cursor:'pointer',fontSize:16 }}>
        ×
      </button>
    </div>
  );
}

// ═══════════════════ 辅助 ═══════════════════

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>{label}</span>
      {children}
    </label>
  );
}

const sSelect: React.CSSProperties = {
  background: 'var(--bg-tertiary)', border: '1px solid var(--border-primary)',
  borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)',
  padding: '6px 8px', fontFamily: 'var(--font-sans)', fontSize: 'var(--text-sm)', outline: 'none',
};
const sInput: React.CSSProperties = {
  background: 'var(--bg-tertiary)', border: '1px solid var(--border-primary)',
  borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)',
  padding: '6px 8px', fontFamily: 'var(--font-sans)', fontSize: 'var(--text-sm)', outline: 'none',
};
