import type { PageName } from './Layout';

interface Props {
  pages: readonly string[];
  active: PageName;
  onNavigate: (p: PageName) => void;
  backendReady: boolean;
}

export default function Sidebar({ pages, active, onNavigate, backendReady }: Props) {
  return (
    <nav style={{
      width: 200,
      minWidth: 200,
      background: 'var(--bg-secondary)',
      borderRight: '1px solid var(--border-primary)',
      display: 'flex',
      flexDirection: 'column',
      padding: 'var(--gap-md)',
      gap: 4,
    }}>
      {/* 标题 */}
      <div style={{
        padding: 'var(--gap-sm) var(--gap-md)',
        marginBottom: 'var(--gap-lg)',
      }}>
        <div style={{
          fontSize: 'var(--text-lg)',
          fontWeight: 500,
          color: 'var(--accent)',
          letterSpacing: 2,
        }}>
          RogueMind
        </div>
        <div style={{
          fontSize: 'var(--text-xs)',
          color: 'var(--text-muted)',
          marginTop: 2,
        }}>
          集成战略助手
        </div>
      </div>

      {/* 导航按钮 */}
      {pages.map((p) => (
        <button
          key={p}
          onClick={() => onNavigate(p as PageName)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--gap-sm)',
            width: '100%',
            padding: '10px var(--gap-md)',
            border: '1px solid transparent',
            borderRadius: 'var(--radius-sm)',
            background: active === p ? 'var(--bg-tertiary)' : 'transparent',
            color: active === p ? 'var(--accent)' : 'var(--text-secondary)',
            fontFamily: 'var(--font-sans)',
            fontSize: 'var(--text-sm)',
            cursor: 'pointer',
            transition: 'all 150ms ease-out',
            textAlign: 'left',
          }}
        >
          {getIcon(p)}
          {p}
        </button>
      ))}

      {/* 后端状态 */}
      <div style={{ marginTop: 'auto', padding: 'var(--gap-md)' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--gap-sm)',
          fontSize: 'var(--text-xs)',
          color: 'var(--text-muted)',
        }}>
          <span className={`status-dot ${backendReady ? 'ok' : 'err'}`} />
          {backendReady ? '后端已连接' : '后端未连接'}
        </div>
      </div>
    </nav>
  );
}

function getIcon(page: string) {
  const map: Record<string, string> = {
    '状态录入': '◈',
    '策略推荐': '◆',
    'Agent 分析': '◇',
    '设置': '○',
  };
  return map[page] || '·';
}
