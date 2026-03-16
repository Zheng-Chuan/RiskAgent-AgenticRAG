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
from typing import Any, List, Optional

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
    include_low_priority: bool = False,
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
    ]

    # 低优先级指标 (默认关闭)
    low_priority_metrics = []
    if include_low_priority:
        low_priority_metrics = [
            (answer_similarity, "answer_similarity", ["embeddings"]),
            (noise_sensitivity, "noise_sensitivity", ["llm"]),
        ]

    # 需要 reference_contexts 的指标
    reference_context_metrics = [
        (context_precision, "context_precision", ["llm"]),
    ]

    # 低优先级 reference 指标 (默认关闭)
    low_priority_reference_metrics = []
    if include_low_priority and has_reference_contexts:
        low_priority_reference_metrics = [
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

    # 添加低优先级指标
    for metric_cls, name, deps in low_priority_metrics:
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

    # 添加低优先级 reference 指标
    for metric_cls, name, deps in low_priority_reference_metrics:
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
    
    # 计算新增指标：无 Reference 的 Context Precision 和 Contradiction Detection
    try:
        cp_no_ref_scores = []
        contradiction_scores = []
        
        for s in samples:
            question = str(s.get("question", ""))
            answer = str(s.get("answer", ""))
            contexts = [str(c) for c in s.get("contexts", []) if c]
            
            # 计算 Context Precision (No Reference)
            if question and contexts:
                try:
                    cp_result = compute_context_precision_no_ref(question, contexts, llm=llm)
                    cp_no_ref_scores.append(cp_result.score)
                except Exception:
                    cp_no_ref_scores.append(0.0)
            
            # 计算 Contradiction Detection
            if question and answer and contexts:
                try:
                    cont_result = compute_contradiction_detection(question, answer, contexts, llm=llm)
                    contradiction_scores.append(cont_result.contradiction_score)
                except Exception:
                    contradiction_scores.append(0.0)
        
        # 添加到结果
        if cp_no_ref_scores:
            valid_cp = [s for s in cp_no_ref_scores if s is not None]
            if valid_cp:
                metrics_out["ragas_context_precision_no_ref"] = sum(valid_cp) / len(valid_cp)
                raw_scores["ragas_context_precision_no_ref"] = valid_cp
        
        if contradiction_scores:
            valid_cont = [s for s in contradiction_scores if s is not None]
            if valid_cont:
                metrics_out["ragas_contradiction_score"] = sum(valid_cont) / len(valid_cont)
                raw_scores["ragas_contradiction_score"] = valid_cont
    except Exception as e:
        pass
    
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


# ---------------------------------------------------------------------------
# 兼容旧版 ragas_integration 接口 (已合并)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RagasResult:
    """旧版 RAGAS 结果容器, 兼容 ragas_integration.try_compute_ragas_metrics."""
    enabled: bool
    ok: bool
    metrics: dict[str, float]
    error: Optional[str] = None


def try_compute_ragas_metrics(
    *,
    samples: list[dict[str, Any]],
    include_reference_based: bool = True,
) -> RagasResult:
    """旧版兼容入口, 内部委托给 compute_all_ragas_metrics."""
    result = compute_all_ragas_metrics(
        samples=samples,
        include_reference_based=include_reference_based,
        include_context_precision=include_reference_based,
    )
    return RagasResult(
        enabled=result.enabled,
        ok=result.ok,
        metrics=result.metrics,
        error=result.error,
    )


# ---------------------------------------------------------------------------
# 新增指标: 无 Reference 版本的 Context Precision & Contradiction Detection
# ---------------------------------------------------------------------------


@dataclass
class ContextPrecisionNoRefResult:
    """无 Reference 的 Context Precision 结果."""
    score: float
    per_context_scores: List[float]
    reasoning: str


def compute_context_precision_no_ref(
    question: str,
    contexts: List[str],
    llm: Any = None,
) -> ContextPrecisionNoRefResult:
    """计算无 Reference 版本的 Context Precision.
    
    使用 LLM 判断每个检索到的上下文片段是否与问题相关，
    不需要 reference_contexts 标注数据。
    
    Args:
        question: 用户问题
        contexts: 检索到的上下文列表
        llm: LLM 实例 (可选，内部会自动创建)
    
    Returns:
        ContextPrecisionNoRefResult 包含分数和详细信息
    """
    from riskagent_agenticrag.llm.generate import call_llm_json

    if llm is None:
        llm = _get_ragas_llm()

    per_context_scores = []
    relevant_count = 0

    prompt_template = """你是一个信息检索质量评估专家。请判断给定的上下文片段是否与用户问题相关。

用户问题: {question}

上下文片段:
{context}

请判断这个上下文片段是否与问题相关:
- 相关: 这个片段包含可以帮助回答问题的信息
- 不相关: 这个片段与问题无关或没有帮助

以JSON格式返回:
{{
  "is_relevant": true/false,
  "confidence": 0.0-1.0,
  "reason": "简短说明"
}}"""

    for idx, ctx in enumerate(contexts):
        prompt = prompt_template.format(
            question=question,
            context=ctx[:1500] if len(ctx) > 1500 else ctx
        )
        try:
            result = call_llm_json(prompt, temperature=0.0)
            is_relevant = bool(result.get("is_relevant", False))
            confidence = float(result.get("confidence", 0.5))
            score = confidence if is_relevant else 0.0
            per_context_scores.append(score)
            if is_relevant:
                relevant_count += 1
        except Exception:
            per_context_scores.append(0.0)

    avg_score = sum(per_context_scores) / len(per_context_scores) if per_context_scores else 0.0

    return ContextPrecisionNoRefResult(
        score=avg_score,
        per_context_scores=per_context_scores,
        reasoning=f"评估了 {len(contexts)} 个上下文片段，{relevant_count} 个被判定为相关"
    )


@dataclass
class ContradictionDetectionResult:
    """矛盾检测结果."""
    has_contradiction: bool
    contradiction_score: float
    contradiction_details: List[dict]


def compute_contradiction_detection(
    question: str,
    answer: str,
    contexts: List[str],
    llm: Any = None,
) -> ContradictionDetectionResult:
    """检测答案与上下文之间是否存在矛盾，以及答案内部是否自相矛盾.
    
    Args:
        question: 用户问题
        answer: 生成的答案
        contexts: 检索到的上下文
        llm: LLM 实例 (可选)
    
    Returns:
        ContradictionDetectionResult
    """
    from riskagent_agenticrag.llm.generate import call_llm_json

    if llm is None:
        llm = _get_ragas_llm()

    contradiction_details = []

    context_text = "\n\n".join([f"[Context {i+1}]\n{ctx[:1000]}" for i, ctx in enumerate(contexts)])

    prompt = """你是一个事实一致性检查专家。请检查以下内容是否存在矛盾：

1. 答案与检索上下文之间是否存在矛盾
2. 答案内部是否存在自相矛盾

用户问题: {question}

检索上下文:
{context_text}

生成的答案:
{answer}

请分析是否存在矛盾，并以JSON格式返回:
{{
  "has_contradiction": true/false,
  "contradiction_score": 0.0-1.0 (0=无矛盾, 1=严重矛盾),
  "details": [
    {{
      "type": "answer_context_contradiction" 或 "answer_internal_contradiction",
      "description": "矛盾描述",
      "severity": "low"/"medium"/"high"
    }}
  ]
}}"""

    try:
        result = call_llm_json(
            prompt.format(
                question=question,
                context_text=context_text,
                answer=answer[:3000] if len(answer) > 3000 else answer
            ),
            temperature=0.0
        )
        has_contradiction = bool(result.get("has_contradiction", False))
        contradiction_score = float(result.get("contradiction_score", 0.0))
        details = result.get("details", [])
        if isinstance(details, list):
            contradiction_details = details
    except Exception:
        has_contradiction = False
        contradiction_score = 0.0
        contradiction_details = []

    return ContradictionDetectionResult(
        has_contradiction=has_contradiction,
        contradiction_score=contradiction_score,
        contradiction_details=contradiction_details
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
        "ragas_context_precision_no_ref": {
            "name": "Context Precision (No Reference)",
            "category": "上下文质量",
            "description": "无标注数据版本的 Context Precision，用 LLM 判断上下文相关性",
            "range": "0-1",
            "requires": "无",
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
            "priority": "low",
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
            "priority": "low",
        },
        # 真实性与幻觉
        "ragas_contradiction_score": {
            "name": "Contradiction Score",
            "category": "真实性与幻觉",
            "description": "答案与上下文之间或答案内部的矛盾程度",
            "range": "0-1",
            "requires": "无",
        },
        # 鲁棒性
        "ragas_noise_sensitivity": {
            "name": "Noise Sensitivity",
            "category": "鲁棒性",
            "description": "系统对噪声上下文的敏感程度",
            "range": "0-1",
            "requires": "无",
            "priority": "low",
        },
        "ragas_response_completeness": {
            "name": "Response Completeness",
            "category": "鲁棒性",
            "description": "答案是否完整覆盖了问题要求",
            "range": "0-1",
            "requires": "无",
        },
    }
