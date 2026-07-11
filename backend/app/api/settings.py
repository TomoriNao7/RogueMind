"""设置 API 路由 — LLM 配置管理."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..core import llm_config

router = APIRouter(prefix="/api/settings", tags=["settings"])


class LLMConfigRequest(BaseModel):
    """LLM 配置请求体."""
    provider: str = Field(description="模型提供商 ID")
    base_url: str = Field(description="API 地址")
    api_key: str = Field(description="API Key")
    model_name: str = Field(description="模型名称")


@router.get("/llm")
async def get_llm_config():
    """获取当前 LLM 配置（API Key 脱敏）."""
    config = llm_config.get_masked_config()
    return {
        "success": True,
        "data": {
            "config": config,
            "configured": llm_config.is_configured(),
        },
        "error": None,
    }


@router.post("/llm")
async def set_llm_config(req: LLMConfigRequest):
    """保存 LLM 配置."""
    llm_config.save_config(req.provider, req.base_url, req.api_key, req.model_name)
    return {
        "success": True,
        "data": {"message": "配置已保存", "configured": True},
        "error": None,
    }


@router.get("/models")
async def get_model_presets():
    """获取预设模型列表（供前端下拉框使用）."""
    return {
        "success": True,
        "data": {"presets": llm_config.MODEL_PRESETS},
        "error": None,
    }
