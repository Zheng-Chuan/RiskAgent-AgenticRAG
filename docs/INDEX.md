# Indexing 模块

Indexing 模块负责文档的加载、预处理、分块、向量化和索引构建，是 RAG 系统的数据基础。

## 模块职责

| 职责 | 说明 |
|------|------|
| 文档加载 | 支持 PDF、Word、HTML、Markdown 等多种格式 |
| 文档预处理 | 清理格式、移除噪音 |
| 文档分块 | 智能分块策略，保持语义完整性 |
| 向量化 | 生成 Dense Embedding 和 Sparse Index |
| 索引构建 | 构建 Milvus 向量索引 |
| 增量索引 | 支持增量添加新文档 |

## 主要文件

| 文件 | 说明 |
|------|------|
| `indexing/indexer.py` | 索引构建器，协调整个索引流程 |
| `indexing/milvus_store.py` | Milvus 存储封装 |
| `rag/chunking.py` | 文档分块策略 |
| `rag/embeddings.py` | 向量化（Dense Embedding） |
| `rag/sparse_index.py` | 关键词索引（Sparse Index） |
| `rag/source_loader.py` | 文档加载器 |
| `rag/ingestion.py` | 文档摄入管道 |

## 使用方式

### 1. CLI 方式

```bash
# 构建全量索引
python -m riskagent_agenticrag.cli index \
  --corpus-dir corpus \
  --persist-dir .milvus

# 增量索引
python -m riskagent_agenticrag.cli index \
  --corpus-dir corpus/new_docs \
  --persist-dir .milvus \
  --incremental
```

### 2. 代码方式

```python
from riskagent_agenticrag.indexing.indexer import build_or_update_index

result = build_or_update_index(
    corpus_dir=Path("corpus"),
    persist_dir=Path(".milvus"),
    include_paths=None,
)
```

## 分块策略

默认使用递归字符分块 (Recursive Character Splitting)，配合：
- 段落边界优先
- 保持语义完整性
- 可配置 chunk size 和 overlap

## 索引类型

| 类型 | 说明 |
|------|------|
| Dense Index | 向量索引，使用 BAAI/bge-large-zh-v1.5 |
| Sparse Index | 关键词索引，使用 BM25 |

## 增量索引

增量索引会：
1. 检查已索引文档的哈希值
2. 只处理新增或修改的文档
3. 保持索引的一致性

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md) - 系统架构
- [DATA.md](./DATA.md) - 数据说明
