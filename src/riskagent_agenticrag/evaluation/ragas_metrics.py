"""RAGAS Metrics - Complete Integration.

全量 RAGAS 指标集成，支持所有官方指标：

上下文质量指标 (Context Quality):
- context_precision: 检索上下文的精确度
- context_recall: 检索上下文的召回率
- context_relevancy: 上下文与查询的相关性
- context_entity_recall: 实体召回率

答案质量指标 (Answer Quality):
- faithfulness: 答案忠实度（基于上下文）
- answer_relevancy: 答案与查询的相关性
- answer_correctness: 答案正确性（vs 参考答案）
- answer_similarity: 答案与参考答案的相似度

鲁棒性指标 (Robustness):
- noise_sensitivity: 对噪声的敏感度
- response_completeness: 回答完整性
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from riskagent_agenticrag.config.settings import settings


@dataclass(frozen=True)
class RagasMetricsResult:
    """RAGAS 评估结果容器."""
    enabled: bool
    ok: bool
    metrics: dict[str, float]
    raw_scores: dict[str, list[float]]  # Per-sample scores
    error: Optional[str] = None


# 指标分类定义
METRIC_CATEGORIES = {
    "context_quality": {
        "name": "上下文质量",
        "description": "评估检索到的上下文质量",
        "metrics": [
            "context_precision",   # 检索精确度
            "context_recall",      # 检索召回率
            "context_relevancy",   # 上下文相关性
            "context_entity_recall", # 实体召回率
        ],
    },
    "answer_quality": {
        "name": "答案质量",
        "description": "评估生成答案的质量",
        "metrics": [
            "faithfulness",        # 忠实度（是否基于上下文）
            "answer_relevancy",    # 答案相关性
            "answer_correctness",  # 答案正确性
            "answer_similarity",   # 答案相似度
        ],
    },
    "robustness": {
        "name": "鲁棒性",
        "description": "评估系统对噪声和边缘情况的处理",
        "metrics": [
            "noise_sensitivity",   # 噪声敏感度
            "response_completeness", # 回答完整性
        ],
    },
}

# 指标依赖的数据字段
METRIC_REQUIREMENTS = {
    # 基础指标（只需要 question, answer, contexts）
    "faithfulness": {"required": ["question", "answer", "contexts"], "optional": []},
    "answer_relevancy": {"required": ["question", "answer", "contexts"], "optional": []},
    "context_relevancy": {"required": ["question", "contexts"], "optional": []},
    
    # 需要 ground_truth（参考答案）
    "context_recall": {"required": ["question", "contexts", "ground_truth"], "optional": []},
    "answer_correctness": {"required": ["question", "answer", "ground_truth"], "optional": []},
    "answer_similarity": {"required": ["question", "answer", "ground_truth"], "optional": []},
    
    # 需要 reference（参考上下文）
    "context_precision": {"required": ["question", "contexts", "reference"], "optional": []},
    "context_entity_recall": {"required": ["question", "contexts", "reference"], "optional": []},
    
    # 需要特殊处理
    "noise_sensitivity": {"required": ["question", "answer", "contexts"], "optional": ["noise_rate"]},
    "response_completeness": {"required": ["question", "answer", "contexts"], "optional": []},
}


def _get_ragas_llm() -> Any:
    """创建 RAGAS 兼容的 LLM."""
    from ragas.llms import llm_factory
    
    from openai import OpenAI
    
    api_key = settings.llm.api_key
    if not api_key:
        raise RuntimeError("Missing API key")
    
    client = OpenAI(
        api_key=api_key,
        base_url=settings.llm.base_url,
    )
    
    model_name = settings.llm.model or "qwen3-8b"
    extra_kwargs = {}
    if "qwen3" in model_name.lower():
        extra_kwargs["extra_body"] = {"enable_thinking": False}
    
    return llm_factory(
        model=model_name,
        provider="openai",
        client=client,
        max_tokens=4096,
        **extra_kwargs
    )


def _get_ragas_embeddings() -> Any:
    """创建 RAGAS 兼容的 Embeddings."""
    from sentence_transformers import SentenceTransformer
    
    model_name = settings.embeddings.model_name or "sentence-transformers/all-MiniLM-L6-v2"
    
    class RagasEmbeddingsWrapper:
        def __init__(self, model_name: str):
            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
        
        def embed_query(self, text: str) -> list[float]:
            result = self.model.encode(text)
            return result.tolist() if hasattr(result, 'tolist') else list(result)
        
        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            results = self.model.encode(texts)
            return [r.tolist() if hasattr(r, 'tolist') else list(r) for r in results]
    
    return RagasEmbeddingsWrapper(model_name)


def compute_all_ragas_metrics(
    *,
    samples: list[dict[str, Any]],
    include_reference_based: bool = True,
    include_context_precision: bool = True,
) -> RagasMetricsResult:
    """计算所有 RAGAS 指标.
    
    Args:
        samples: 评估样本列表
        include_reference_based: 是否包含需要 reference_answer 的指标
        include_context_precision: 是否包含 context_precision（需要 reference_contexts）
    
    Returns:
        RagasMetricsResult 包含所有指标结果
    """
    import warnings
    warnings.filterwarnings('ignore', category=DeprecationWarning, module='ragas')
    
    try:
        from datasets import Dataset
    except ImportError as e:
        return RagasMetricsResult(
            enabled=True, ok=False, metrics={}, raw_scores={}, error=f"datasets not available: {e}"
        )
    
    try:
        # 全量导入 RAGAS 指标
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            answer_correctness,
            answer_similarity,
            context_precision,
            context_recall,
            context_relevancy,
            context_entity_recall,
            noise_sensitivity,
            response_completeness,
        )
    except ImportError as e:
        return RagasMetricsResult(
            enabled=True, ok=False, metrics={}, raw_scores={}, error=f"ragas metrics import failed: {e}"
        )
    
    # 准备数据
    rows = []
    has_ground_truth = False
    has_reference_contexts = False
    
    for s in samples:
        row = {
            "question": str(s.get("question", "")),
            "answer": str(s.get("answer", "")),
            "contexts": [str(c) for c in s.get("contexts", []) if c],
        }
        
        # ground_truth (参考答案)
        ref_answer = s.get("reference_answer")
        if ref_answer:
            row["ground_truth"] = str(ref_answer)
            has_ground_truth = True
        
        # reference (参考上下文，用于 context_precision)
        ref_ctx = s.get("reference_contexts")
        if ref_ctx and isinstance(ref_ctx, list) and ref_ctx:
            row["reference"] = [str(c) for c in ref_ctx if c]
            has_reference_contexts = True
        
        rows.append(row)
    
    if not rows:
        return RagasMetricsResult(
            enabled=True, ok=False, metrics={}, raw_scores={}, error="no samples provided"
        )
    
    ds = Dataset.from_list(rows)
    
    # 初始化 LLM 和 Embeddings
    try:
        llm = _get_ragas_llm()
        embeddings = _get_ragas_embeddings()
    except Exception as e:
        return RagasMetricsResult(
            enabled=True, ok=False, metrics={}, raw_scores={}, error=f"setup failed: {e}"
        )
    
    # 构建指标列表
    metrics_list = []
    enabled_metrics = []
    
    # 基础指标（始终启用）
    base_metrics = [
        (faithfulness, "faithfulness", ["llm"]),
        (answer_relevancy, "answer_relevancy", ["llm", "embeddings"]),
        (context_relevancy, "context_relevancy", ["llm"]),
        (response_completeness, "response_completeness", ["llm"]),
    ]
    
    # 需要 ground_truth 的指标
    ground_truth_metrics = [
        (context_recall, "context_recall", ["llm"]),
        (answer_correctness, "answer_correctness", ["llm", "embeddings"]),
        (answer_similarity, "answer_similarity", ["embeddings"]),
    ]
    
    # 需要 reference_contexts 的指标
    reference_context_metrics = [
        (context_precision, "context_precision", ["llm"]),
        (context_entity_recall, "context_entity_recall", ["llm"]),
    ]
    
    # 添加基础指标
    for metric_cls, name, deps in base_metrics:
        m = metric_cls.__class__()
        m.llm = llm
        if "embeddings" in deps:
            m.embeddings = embeddings
        metrics_list.append(m)
        enabled_metrics.append(name)
    
    # 添加需要 ground_truth 的指标
    if include_reference_based and has_ground_truth:
        for metric_cls, name, deps in ground_truth_metrics:
            m = metric_cls.__class__()
            m.llm = llm
            if "embeddings" in deps:
                m.embeddings = embeddings
            metrics_list.append(m)
            enabled_metrics.append(name)
    
    # 添加需要 reference_contexts 的指标
    if include_context_precision and has_reference_contexts:
        for metric_cls, name, deps in reference_context_metrics:
            m = metric_cls.__class__()
            m.llm = llm
            if "embeddings" in deps:
                m.embeddings = embeddings
            metrics_list.append(m)
            enabled_metrics.append(name)
    
    if not metrics_list:
        return RagasMetricsResult(
            enabled=True, ok=False, metrics={}, raw_scores={}, error="no metrics to evaluate"
        )
    
    # 执行评估
    try:
        from ragas import evaluate
        result = evaluate(
            dataset=ds,
            metrics=metrics_list,
            llm=llm,
            embeddings=embeddings,
        )
    except Exception as e:
        return RagasMetricsResult(
            enabled=True, ok=False, metrics={}, raw_scores={}, error=f"evaluation failed: {e}"
        )
    
    # 提取结果
    metrics_out = {}
    raw_scores = {}
    
    try:
        if hasattr(result, '_scores_dict'):
            for metric_name, values in result._scores_dict.items():
                valid_values = [float(v) for v in values if v is not None]
                if valid_values:
                    key = f"ragas_{metric_name}"
                    metrics_out[key] = sum(valid_values) / len(valid_values)
                    raw_scores[key] = valid_values
    except Exception as e:
        return RagasMetricsResult(
            enabled=True, ok=False, metrics={}, raw_scores={}, error=f"result extraction failed: {e}"
        )
    
    # 添加元数据
    metrics_out["ragas_samples_evaluated"] = len(rows)
    metrics_out["ragas_enabled_metrics_count"] = len(enabled_metrics)
    
    return RagasMetricsResult(
        enabled=True,
        ok=True,
        metrics=metrics_out,
        raw_scores=raw_scores,
        error=None,
    )


def get_all_metrics_description() -> dict[str, dict[str, str]]:
    """获取所有指标的详细说明."""
    return {
        # 上下文质量
        "ragas_context_precision": {
            "name": "Context Precision",
            "category": "上下文质量",
            "description": "检索到的上下文中有多少是相关的",
            "range": "0-1",
            "requires": "reference_contexts",
        },
        "ragas_context_recall": {
            "name": "Context Recall",
            "category": "上下文质量",
            "description": "相关上下文有多少被成功检索到",
            "range": "0-1",
            "requires": "reference_answer",
        },
        "ragas_context_relevancy": {
            "name": "Context Relevancy",
            "category": "上下文质量",
            "description": "上下文与查询问题的相关程度",
            "range": "0-1",
            "requires": "无",
        },
        "ragas_context_entity_recall": {
            "name": "Context Entity Recall",
            "category": "上下文质量",
            "description": "上下文中实体的召回率",
            "range": "0-1",
            "requires": "reference_contexts",
        },
        # 答案质量
        "ragas_faithfulness": {
            "name": "Faithfulness",
            "category": "答案质量",
            "description": "答案是否忠实于检索到的上下文",
            "range": "0-1",
            "requires": "无",
        },
        "ragas_answer_relevancy": {
            "name": "Answer Relevancy",
            "category": "答案质量",
            "description": "答案与问题的相关程度",
            "range": "0-1",
            "requires": "无",
        },
        "ragas_answer_correctness": {
            "name": "Answer Correctness",
            "category": "答案质量",
            "description": "答案相对于参考答案的正确性",
            "range": "0-1",
            "requires": "reference_answer",
        },
        "ragas_answer_similarity": {
            "name": "Answer Similarity",
            "category": "答案质量",
            "description": "答案与参考答案的语义相似度",
            "range": "0-1",
            "requires": "reference_answer",
        },
        # 鲁棒性
        "ragas_noise_sensitivity": {
            "name": "Noise Sensitivity",
            "category": "鲁棒性",
            "description": "系统对噪声上下文的敏感程度",
            "range": "0-1",
            "requires": "无",
        },
        "ragas_response_completeness": {
            "name": "Response Completeness",
            "category": "鲁棒性",
            "description": "答案是否完整覆盖了问题要求",
            "range": "0-1",
            "requires": "无",
        },
    }
