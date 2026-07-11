"""LLM 配置管理 — 存储和读取用户的 API Key 和模型设置."""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent / "data" / "llm_config.json"

# 预设模型列表（前端下拉框展示）
MODEL_PRESETS = [
    {"id": "claude", "name": "Claude (Anthropic)", "base_url": "https://api.anthropic.com/v1", "models": ["claude-sonnet-5-20251001", "claude-opus-4-8", "claude-haiku-4-5-20251001"]},
    {"id": "openai", "name": "GPT (OpenAI)", "base_url": "https://api.openai.com/v1", "models": ["gpt-4o", "gpt-4o-mini", "gpt-4.1"]},
    {"id": "deepseek", "name": "DeepSeek", "base_url": "https://api.deepseek.com/v1", "models": ["deepseek-chat", "deepseek-reasoner"]},
    {"id": "kimi", "name": "Kimi (月之暗面)", "base_url": "https://api.moonshot.cn/v1", "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"]},
    {"id": "qwen", "name": "Qwen (通义千问)", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "models": ["qwen-turbo", "qwen-plus", "qwen-max"]},
    {"id": "ollama", "name": "Ollama (本地)", "base_url": "http://localhost:11434/v1", "models": ["llama3", "qwen2.5", "deepseek-r1"]},
    {"id": "custom", "name": "自定义（兼容 OpenAI API）", "base_url": "", "models": []},
]


def load_config() -> dict:
    """读取 LLM 配置."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"provider": "", "base_url": "", "api_key": "", "model_name": ""}


def save_config(provider: str, base_url: str, api_key: str, model_name: str) -> dict:
    """保存 LLM 配置."""
    config = {
        "provider": provider,
        "base_url": base_url,
        "api_key": api_key,
        "model_name": model_name,
    }
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return config


def get_masked_config() -> dict:
    """获取配置（API Key 脱敏）."""
    config = load_config()
    key = config.get("api_key", "")
    if key and len(key) > 8:
        config["api_key"] = key[:4] + "****" + key[-4:]
    return config


def is_configured() -> bool:
    """检查是否已配置 LLM."""
    config = load_config()
    return bool(config.get("api_key") and config.get("base_url"))
