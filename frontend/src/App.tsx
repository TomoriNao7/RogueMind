import { useState, useEffect } from 'react';
import Layout, { type PageName } from './components/Layout';
import StateInput from './pages/StateInput';
import Recommend from './pages/Recommend';
import Agent from './pages/Agent';
import Settings from './pages/Settings';
import { useStore } from './store/useStore';
import { healthCheck, createSession, getLLMConfig } from './api/client';

function App() {
  const [page, setPage] = useState<PageName>('状态录入');
  const backendReady = useStore((s) => s.backendReady);
  const setBackendReady = useStore((s) => s.setBackendReady);
  const setSessionId = useStore((s) => s.setSessionId);
  const setConfigured = useStore((s) => s.setLLMConfigured);

  // 启动时检查后端连接、创建会话、加载 LLM 配置
  useEffect(() => {
    healthCheck()
      .then(() => setBackendReady(true))
      .catch(() => setBackendReady(false));

    createSession()
      .then((r) => setSessionId(r.data.session_id))
      .catch(() => {});

    getLLMConfig()
      .then((r) => { if (r.data.configured) setConfigured(true); })
      .catch(() => {});
  }, []);

  return (
    <Layout active={page} onNavigate={setPage} backendReady={backendReady}>
      {page === '状态录入' && <StateInput />}
      {page === '策略推荐' && <Recommend />}
      {page === 'Agent 分析' && <Agent />}
      {page === '设置' && <Settings />}
    </Layout>
  );
}

export default App;
