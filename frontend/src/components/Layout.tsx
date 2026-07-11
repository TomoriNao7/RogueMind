import Sidebar from './Sidebar';

const PAGES = ['状态录入', '策略推荐', 'Agent 分析', '设置'] as const;
export type PageName = (typeof PAGES)[number];

interface Props {
  children: React.ReactNode;
  active: PageName;
  onNavigate: (p: PageName) => void;
  backendReady: boolean;
}

export default function Layout({ children, active, onNavigate, backendReady }: Props) {
  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      <Sidebar
        pages={PAGES}
        active={active}
        onNavigate={onNavigate}
        backendReady={backendReady}
      />
      <main style={{
        flex: 1,
        overflow: 'auto',
        padding: 'var(--gap-lg)',
        background: 'var(--bg-primary)',
      }}>
        {children}
      </main>
    </div>
  );
}
