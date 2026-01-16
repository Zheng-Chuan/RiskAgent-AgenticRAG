# RAGAS 评测指南

本文档介绍如何使用 RAGAS 框架对 RiskAgent-RAG 进行质量评测。

## 1. 概述

我们使用 RAGAS (Retrieval Augmented Generation Assessment) 来量化评估 RAG 系统的性能。
评测主要关注以下几个维度 (RAG Triad + Retrieval):

*   **Faithfulness (忠实度)**: 回答是否忠实于检索到的上下文 (幻觉检测)。
*   **Answer Relevance (答案相关性)**: 回答是否直接切题。
*   **Context Precision (检索精度)**: 检索到的 chunk 中有多少是有用的。
*   **Context Recall (检索召回)**: 检索到的 chunk 是否覆盖了 Ground Truth 所需的信息。

## 2. 准备工作

### 2.1 依赖安装

请确保使用 `LangChain` conda 环境:

```bash
conda activate LangChain
pip install "ragas>=0.1.0" datasets
```

### 2.2 LLM 配置

RAGAS 需要一个 "Judge LLM" 来进行打分。推荐使用 OpenAI GPT-4o 或 GPT-3.5-turbo。

**方式 A: 使用 OpenAI (推荐)**

```bash
export OPENAI_API_KEY="sk-..."
export LLM_MODEL="gpt-4o"
```

**方式 B: 使用 Ollama (本地)**

如果您无法访问 OpenAI，可以使用本地 Ollama 模型 (如 qwen2.5:14b) 作为裁判。
注意: 本地模型评分的一致性可能不如 GPT-4。

```bash
export LLM_PROVIDER="ollama"
export OLLAMA_BASE_URL="http://localhost:11434"
export LLM_MODEL="qwen2.5:14b"
```

## 3. 运行评测

使用 `riskagent_rag.evaluation.run` 模块一键运行评测。

### 3.1 基础命令

```bash
# 运行评测并开启 RAGAS 指标计算
conda run -n LangChain python -m riskagent_rag.evaluation.run --enable-ragas
```

### 3.2 常用参数

*   `--corpus-dir`: 语料目录 (默认 `corpus`)
*   `--dataset`: 评测数据集路径 (默认 `tests/data/questions.json`)
*   `--artifacts-dir`: 报告输出目录 (默认 `.artifacts`)
*   --baseline`: 指定基线报告路径用于对比 (默认自动查找最新)

示例:

```bash
# 使用自定义数据集运行
python -m riskagent_rag.evaluation.run \
    --dataset tests/data/eval_set_v2.json \
    --enable-ragas
```

## 4. 查看报告

评测完成后，会在 `.artifacts/reports/` 目录下生成 JSON 格式的报告。
文件名格式: `report_{timestamp}.json`。

报告包含:
1.  **Metrics**: 汇总指标 (如 `citations_coverage`, `ragas.faithfulness` 等)。
2.  **Samples**: 每条样本的详细输入、输出、引用和单项评分。
3.  **Baseline Diff**: 如果存在基线，会显示指标变化 (diff)。

## 5. 如何新增评测样本

编辑 `tests/data/questions.json` (或新建 JSON 文件)。
Schema 如下:

```json
[
  {
    "id": "q1",
    "question": "What is FRTB?",
    "reference_answer": "FRTB stands for Fundamental Review of the Trading Book...",
    "ground_truth_contexts": [
      "FRTB is a comprehensive suite of capital rules..."
    ]
  }
]
```

*   `reference_answer`: 参考答案 (用于 Answer Relevance / Context Recall)。
*   `ground_truth_contexts`: 事实依据 (用于 Context Recall)。

## 6. 常见问题

**Q: 运行报错 `The api_key client option must be set...`**
A: RAGAS 默认尝试连接 OpenAI。请确保环境变量 `OPENAI_API_KEY` 已设置。如果使用 Ollama，请确保代码中正确配置了 `ChatOllama` 并传入 evaluate 函数 (已在 `ragas_integration.py` 中处理)。

**Q: 评分很慢**
A: RAGAS 需要对每个样本多次调用 LLM。如果使用 GPT-4，速度取决于 API 响应；如果使用本地 Ollama，取决于 GPU 性能。建议先用小数据集 (`tests/data/questions.json`) 调试。
