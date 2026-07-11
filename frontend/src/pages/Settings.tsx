import { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { getModels, getLLMConfig, setLLMConfig } from '../api/client';

interface Preset {
  id: string;
  name: string;
  base_url: string;
  models: string[];
}

export default function Settings() {
  const setConfigured = useStore((s) => s.setLLMConfigured);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [provider, setProvider] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [modelName, setModelName] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getModels().then((r) => {
      setPresets(r.data.presets);
    });
    getLLMConfig().then((r) => {
      if (r.data.configured) {
        setProvider(r.data.config.provider);
        setBaseUrl(r.data.config.base_url);
        setApiKey(r.data.config.api_key);
        setModelName(r.data.config.model_name);
        setConfigured(true);
      }
    });
  }, []);

  const handleProviderChange = (pid: string) => {
    setProvider(pid);
    const preset = presets.find((p) => p.id === pid);
    if (preset) {
      setBaseUrl(preset.base_url);
      if (preset.models.length > 0) setModelName(preset.models[0]);
    }
  };

  const handleSave = async () => {
    await setLLMConfig({ provider, base_url: baseUrl, api_key: apiKey, model_name: modelName });
    setSaved(true);
    setConfigured(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const selectedPreset = presets.find((p) => p.id === provider);

  return (
    <div style={{ maxWidth: 600 }}>
      <h1 style={{ color: 'var(--accent)', marginBottom: 24 }}>设置</h1>

      {/* LLM 配置 */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h2 style={{ marginBottom: 16 }}>LLM 配置</h2>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Field label="模型提供商">
            <select value={provider} onChange={(e) => handleProviderChange(e.target.value)}
              style={selectStyle}>
              <option value="">选择提供商</option>
              {presets.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </Field>

          <Field label="API 地址">
            <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://api.openai.com/v1" style={inputStyle} />
          </Field>

          <Field label="API Key">
            <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..." style={inputStyle} />
          </Field>

          <Field label="模型名称">
            {selectedPreset && selectedPreset.models.length > 0 ? (
              <select value={modelName} onChange={(e) => setModelName(e.target.value)}
                style={selectStyle}>
                {selectedPreset.models.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            ) : (
              <input value={modelName} onChange={(e) => setModelName(e.target.value)}
                placeholder="model-name" style={inputStyle} />
            )}
          </Field>
        </div>

        <button className="btn" onClick={handleSave}
          style={{ marginTop: 16 }}>
          {saved ? '已保存' : '保存配置'}
        </button>
      </div>

      {/* 关于 */}
      <div className="card">
        <h2 style={{ marginBottom: 8 }}>关于</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', lineHeight: 1.6 }}>
          RogueMind v0.1.0<br />
          明日方舟集成战略助手<br />
          鹰角网络美术风格 · 黑白主题
        </p>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>{label}</span>
      {children}
    </label>
  );
}

const selectStyle: React.CSSProperties = {
  background: 'var(--bg-tertiary)',
  border: '1px solid var(--border-primary)',
  borderRadius: 'var(--radius-sm)',
  color: 'var(--text-primary)',
  padding: '8px',
  fontFamily: 'var(--font-sans)',
  fontSize: 'var(--text-sm)',
  outline: 'none',
};

const inputStyle: React.CSSProperties = {
  background: 'var(--bg-tertiary)',
  border: '1px solid var(--border-primary)',
  borderRadius: 'var(--radius-sm)',
  color: 'var(--text-primary)',
  padding: '8px',
  fontFamily: 'var(--font-sans)',
  fontSize: 'var(--text-sm)',
  outline: 'none',
};
