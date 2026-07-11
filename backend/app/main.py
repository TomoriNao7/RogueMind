"""RogueMind FastAPI 应用入口."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import knowledge, recommend, settings, analyze, session_api
from .core import rag, session


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化 RAG，清理过期会话."""
    rag.initialize()
    cleaned = session.cleanup_expired()
    if cleaned:
        print(f"已清理 {cleaned} 个过期会话")
    yield


app = FastAPI(
    title="RogueMind",
    description="明日方舟集成战略助手 API",
    version="0.1.0",
    lifespan=lifespan,
)

# 跨域中间件（开发阶段允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(knowledge.router)
app.include_router(recommend.router)
app.include_router(settings.router)
app.include_router(analyze.router)
app.include_router(session_api.router)


@app.get("/api/health")
async def health_check():
    """健康检查端点."""
    return {
        "success": True,
        "data": {
            "status": "ok",
            "version": "0.1.0",
            "rag_ready": rag.is_ready(),
        },
        "error": None,
    }
