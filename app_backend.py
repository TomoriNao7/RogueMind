"""PyInstaller 入口 — 独立运行 FastAPI 后端服务."""
import sys
import os

# ═══════════════════════════════════════════
# 关键：非 frozen 时导入 app.main，让 PyInstaller
# 在分析阶段追踪到 fastapi/pydantic/openai 等所有依赖
# ═══════════════════════════════════════════
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))
    import app.main  # noqa: F401 — 触发 PyInstaller 依赖追踪


def main():
    """启动 Uvicorn 服务器."""
    import uvicorn

    # PyInstaller --noconsole 模式下 sys.stdout/stderr 为 None，
    # uvicorn 会调用 sys.stdout.isatty() 导致 AttributeError
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w')

    if getattr(sys, 'frozen', False):
        # _MEIPASS 是 PyInstaller 数据解压目录，--add-data 的文件都在这里
        # 必须加入 sys.path，否则 app.* 等 Python 包无法被 import
        if sys._MEIPASS not in sys.path:
            sys.path.insert(0, sys._MEIPASS)

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
