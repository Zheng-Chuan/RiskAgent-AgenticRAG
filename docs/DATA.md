# 数据说明

本文档说明 RiskAgent-AgenticRAG 项目中涉及的各类数据。

## 1. 语料库 (Corpus)

### 目录结构
```
corpus/
├── acceptance/           # 验收测试文档
├── regulatory_seed/      # 监管文档
│   ├── md/en/           # Markdown 格式
│   └── pdf/en/          # PDF 格式
└── Background.md        # 背景知识
```

### 支持格式

| 格式 | 说明 |
|------|------|
| PDF | `.pdf`，金融监管文档 |
| Word | `.docx` |
| Markdown | `.md` |
| HTML | `.html` |

### 内容主题

- FRTB (Fundamental Review of the Trading Book)
- CVA (Credit Valuation Adjustment)
- XVA 系列
- Basel III
- 金融风险术语

---

## 2. 测试数据集

### 位置
`tests/data/questions.json`

### 数据结构
```json
{
  "item_id": "q01",
  "question": "What is FRTB?",
  "reference_answer": "...",
  "reference_contexts": [...],
  "ground_truth_contexts": [...]
}
```

### 字段说明

| 字段 | 说明 | 是否必需 |
|------|------|---------|
| `item_id` | 问题 ID | 是 |
| `question` | 用户问题 | 是 |
| `reference_answer` | 参考答案 | 否 |
| `reference_contexts` | 参考上下文 | 否 |
| `ground_truth_contexts` | 真实上下文 | 否 |

---

## 3. 索引数据

### 位置
`.milvus/`

### 目录结构
```
.milvus/
├── milvus_lite/          # Milvus Lite 数据
└── index_manifest.json   # 索引清单
```

### index_manifest.json
记录已索引文档的元数据：
- 文档路径
- 最后修改时间
- 哈希值
- 分块信息

---

## 4. 评估 Artifacts

### 位置
`.artifacts/`

### 目录结构
```
.artifacts/
├── artifacts/            # 单次请求的 artifacts
│   └── <id>/
│       ├── trace.json    # 完整 trace
│       └── ...
└── reports/              # 评估报告
    ├── rag_eval_*.md     # Markdown 报告
    ├── rag_eval_*.json   # JSON 报告
    └── ...
```

---

## 5. 配置数据

### 阈值配置
`docs/eval_thresholds.yaml` - 评估指标阈值和门禁策略

### 环境变量
- `OPENROUTER_API_KEY` - LLM API Key
- `EMBEDDINGS_PROVIDER` - 嵌入模型提供者

---

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md) - 系统架构
- [INDEX.md](./INDEX.md) - Indexing 模块
- [EVALUATION.md](./EVALUATION.md) - 评估模块
