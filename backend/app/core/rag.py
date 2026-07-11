"""RAG 混合检索模块 — BM25 关键词 + BGE 向量 + RRF 融合排序，FAISS 向量索引."""

import sys
from pathlib import Path
from typing import Optional

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

# 路径配置 — 兼容 PyInstaller 打包
if getattr(sys, 'frozen', False):
    _BASE = Path(sys._MEIPASS)
else:
    _BASE = Path(__file__).parent.parent.parent

MODEL_DIR = _BASE / "models" / "models" / "BAAI--bge-small-zh-v1.5" / "snapshots" / "master"
KNOWLEDGE_DIR = _BASE / "data"
INDEX_PATH = _BASE / "data" / "faiss_index.bin"

# 全局状态
_model: Optional[SentenceTransformer] = None
_bm25: Optional[BM25Okapi] = None
_bm25_docs: list[dict] = []
_faiss_index: Optional[faiss.Index] = None
_ready = False


def _load_model():
    """加载 BGE 向量模型."""
    global _model
    if _model is not None:
        return
    _model = SentenceTransformer(str(MODEL_DIR))


def _tokenize(text: str) -> list[str]:
    """中文分词：字符级 unigram + bigram."""
    text = text.strip()
    if not text:
        return []
    tokens = []
    for i in range(len(text)):
        tokens.append(text[i])
    for i in range(len(text) - 1):
        tokens.append(text[i:i + 2])
    return tokens


# ═══════════════════ 初始化 ═══════════════════

def initialize() -> bool:
    """初始化 RAG 系统：加载模型，构建 BM25 索引和 FAISS 向量索引."""
    global _ready, _bm25, _bm25_docs, _faiss_index

    # 加载 BGE 模型
    try:
        _load_model()
    except Exception as e:
        print(f"RAG 初始化失败（模型加载）: {e}")
        return False

    # 加载知识文档
    _bm25_docs = _load_knowledge_docs()
    if not _bm25_docs:
        print("RAG 初始化：未找到知识文档")
        _ready = True
        return True

    # 构建 BM25 关键词索引
    tokenized = [_tokenize(d["content"]) for d in _bm25_docs]
    _bm25 = BM25Okapi(tokenized)

    # 构建 FAISS 向量索引（余弦相似度 = 内积 on 归一化向量）
    texts = [d["content"] for d in _bm25_docs]
    embeddings = _model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    dim = embeddings.shape[1]
    _faiss_index = faiss.IndexFlatIP(dim)  # IP = Inner Product，归一化后即余弦相似度
    _faiss_index.add(embeddings.astype(np.float32))

    # 持久化 FAISS 索引到磁盘
    faiss.write_index(_faiss_index, str(INDEX_PATH))

    _ready = True
    print(f"RAG 就绪：{len(_bm25_docs)} 篇文档已索引")
    return True


def _load_knowledge_docs() -> list[dict]:
    """加载知识文档，将大文档按 ## 标题拆分为段落."""
    docs = []
    flow_path = KNOWLEDGE_DIR / "界园肉鸽大致流程.md"
    if flow_path.exists():
        with open(flow_path, encoding="utf-8") as f:
            content = f.read()
            sections = content.split("\n## ")
            for sec in sections:
                sec = sec.strip()
                if not sec:
                    continue
                title = sec.split("\n")[0].replace("# ", "").strip()[:80]
                docs.append({
                    "id": f"guide_jy_{abs(hash(sec)):08x}",
                    "title": title,
                    "content": sec[:3000],
                    "source": "界园肉鸽大致流程.md",
                })
    return docs


# ═══════════════════ 检索 ═══════════════════

def search(query: str, top_k: int = 5) -> list[dict]:
    """混合检索：BM25 + FAISS 向量，RRF 融合排序.

    Args:
        query: 用户查询文本
        top_k: 返回结果数量

    Returns:
        排序后的文档列表，每项包含 id, title, content, score, source
    """
    if not _ready:
        initialize()

    if not _bm25_docs:
        return []

    # 1. BM25 关键词匹配得分
    bm25_scores = np.array(_bm25.get_scores(_tokenize(query))) if _bm25 else np.ones(len(_bm25_docs))

    # 2. FAISS 向量语义检索得分
    query_vec = _model.encode([query], normalize_embeddings=True).astype(np.float32)
    vec_scores, _ = _faiss_index.search(query_vec, len(_bm25_docs))
    # 将 FAISS 返回的 (id, score) 映射回文档序号的得分数组
    vec_score_arr = np.zeros(len(_bm25_docs))
    for idx, score in zip(_[0], vec_scores[0]):
        if idx < len(vec_score_arr):
            vec_score_arr[idx] = score

    # 3. RRF 融合排序
    fused = _rrf_fuse([
        ("bm25", bm25_scores),
        ("vector", vec_score_arr),
    ])

    # 4. 按融合得分降序排列，取 top_k
    ranked = sorted(enumerate(fused), key=lambda x: x[1], reverse=True)

    output = []
    for idx, score in ranked[:top_k]:
        doc = _bm25_docs[idx]
        output.append({
            "id": doc["id"],
            "title": doc["title"],
            "content": doc["content"][:500],
            "score": round(float(score), 4),
            "source": doc.get("source", ""),
        })

    return output


def _rrf_fuse(scored_lists: list[tuple[str, np.ndarray]], k: int = 60) -> np.ndarray:
    """Reciprocal Rank Fusion：将多路排序结果融合为单一排名.

    原理：对于每个文档，计算其在各路排名中的倒数排名，
    求和后取平均作为最终得分。k 参数控制排名的平滑程度。

    Args:
        scored_lists: [(名称, 得分数组), ...]
        k: RRF 平滑参数，默认 60

    Returns:
        融合后的得分数组
    """
    n = len(scored_lists[0][1])
    fused = np.zeros(n)

    for name, scores in scored_lists:
        order = np.argsort(-scores)  # 从高到低排序
        ranks = np.zeros(n)
        for rank, idx in enumerate(order):
            ranks[idx] = 1.0 / (k + rank + 1)
        fused += ranks

    return fused / len(scored_lists)


def is_ready() -> bool:
    """RAG 系统是否就绪."""
    return _ready
