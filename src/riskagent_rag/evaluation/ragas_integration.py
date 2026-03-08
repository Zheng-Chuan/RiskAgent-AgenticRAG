"""RAGAS integration.

RAGAS 质量指标集成 (v0.4.3)
- 使用 ragas.metrics 传统 API
- 使用 OpenAI embeddings 避免 HuggingFace 网络问题
- 使用 gpt-4o-mini 作为评判模型
- 提供 Faithfulness, AnswerRelevancy, ContextRecall, AnswerCorrectness
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from riskagent_rag.config.settings import settings


@dataclass(frozen=True)
class RagasResult:
    enabled: bool
    ok: bool
    metrics: dict[str, float]
    error: Optional[str] = None


def _get_openai_client() -> Any:
    """Create OpenAI client from settings."""
    from openai import OpenAI
    
    api_key = settings.llm.api_key
    if not api_key:
        raise RuntimeError("Missing OpenRouter API key. Set OPENAI_API_KEY (or LLM_API_KEY).")
    
    return OpenAI(
        api_key=api_key,
        base_url=settings.llm.base_url,
    )


def _get_ragas_llm() -> Any:
    """Create RAGAS-compatible InstructorLLM.
    
    Uses gpt-4o-mini for RAGAS evaluation to ensure compatibility.
    """
    from ragas.llms import llm_factory
    
    client = _get_openai_client()
    model_name = "openai/gpt-4o-mini"
    
    return llm_factory(
        model=model_name,
        provider="openai",
        client=client,
    )


def _get_ragas_embeddings() -> Any:
    """Create RAGAS-compatible OpenAI embeddings."""
    from ragas.embeddings import OpenAIEmbeddings
    
    client = _get_openai_client()
    return OpenAIEmbeddings(
        client=client,
        model="openai/text-embedding-3-small",
    )


def try_compute_ragas_metrics(
    *,
    samples: list[dict[str, Any]],
    include_reference_based: bool = True,
) -> RagasResult:
    """Compute RAGAS metrics for evaluation samples.
    
    Uses compatible metrics that work without special column requirements.
    Excludes context_precision which requires 'reference' column mapping.
    
    Args:
        samples: Evaluation samples with question, answer, contexts
        include_reference_based: Whether to include metrics requiring reference_answer
    
    Returns:
        RagasResult with metrics dict containing:
        - faithfulness: Answer groundedness in contexts (0-1)
        - answer_relevancy: Answer relevance to question (0-1)
        - context_recall: Recall based on reference answer (0-1)
        - answer_correctness: Correctness vs reference (0-1)
    """
    import warnings
    warnings.filterwarnings('ignore', category=DeprecationWarning, module='ragas')
    
    try:
        from datasets import Dataset
    except ImportError as e:
        return RagasResult(enabled=True, ok=False, metrics={}, error=f"datasets not available: {e}")

    try:
        # Use legacy RAGAS metrics
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_recall,
            answer_correctness,
        )
    except ImportError as e:
        return RagasResult(enabled=True, ok=False, metrics={}, error=f"ragas metrics not available: {e}")

    # 准备数据
    rows: list[dict[str, Any]] = []
    has_reference = False
    
    for s in samples:
        question = str(s.get("question", ""))
        answer = str(s.get("answer", ""))
        contexts = s.get("contexts")
        if not isinstance(contexts, list):
            contexts = []
        contexts = [str(c) for c in contexts]

        row: dict[str, Any] = {
            "question": question,
            "answer": answer,
            "contexts": contexts,
        }

        # 使用 reference_answer 作为 ground_truth
        ref = s.get("reference_answer")
        if isinstance(ref, str) and ref.strip():
            row["ground_truth"] = ref
            has_reference = True
        elif isinstance(ref, list) and ref:
            row["ground_truth"] = str(ref[0])
            has_reference = True

        rows.append(row)

    if not rows:
        return RagasResult(enabled=True, ok=False, metrics={}, error="no samples provided")

    ds = Dataset.from_list(rows)

    # 准备 RAGAS-compatible LLM 和 Embeddings
    try:
        judge_llm = _get_ragas_llm()
    except Exception as e:
        return RagasResult(enabled=True, ok=False, metrics={}, error=f"LLM setup failed: {e}")
    
    try:
        embeddings = _get_ragas_embeddings()
    except Exception as e:
        return RagasResult(enabled=True, ok=False, metrics={}, error=f"Embeddings setup failed: {e}")

    # 准备 Metrics - 排除 context_precision (需要特殊 reference 列)
    metrics_list = []
    
    # Faithfulness only needs LLM
    faith = faithfulness.__class__()
    faith.llm = judge_llm
    metrics_list.append(faith)
    
    # AnswerRelevancy needs both LLM and embeddings
    relevancy = answer_relevancy.__class__()
    relevancy.llm = judge_llm
    relevancy.embeddings = embeddings
    metrics_list.append(relevancy)
    
    # context_recall 和 answer_correctness 需要 reference_answer
    if include_reference_based and has_reference:
        # ContextRecall needs LLM and ground_truth
        recall = context_recall.__class__()
        recall.llm = judge_llm
        metrics_list.append(recall)
        
        # AnswerCorrectness needs both LLM and embeddings
        correctness = answer_correctness.__class__()
        correctness.llm = judge_llm
        correctness.embeddings = embeddings
        metrics_list.append(correctness)

    if not metrics_list:
        return RagasResult(enabled=True, ok=False, metrics={}, error="no metrics to evaluate")

    # 执行评测
    try:
        from ragas import evaluate
        
        result = evaluate(
            dataset=ds,
            metrics=metrics_list,
            llm=judge_llm,
            embeddings=embeddings,
        )
    except Exception as e:
        return RagasResult(enabled=True, ok=False, metrics={}, error=f"RAGAS evaluation failed: {e}")

    # 提取结果
    metrics_out: dict[str, float] = {}
    try:
        for k, v in result.items():
            try:
                if isinstance(v, (int, float)):
                    metrics_out[f"ragas_{k}"] = float(v)
                elif hasattr(v, 'mean'):
                    metrics_out[f"ragas_{k}"] = float(v.mean())
            except (TypeError, ValueError):
                pass
    except Exception:
        pass

    # 添加元数据
    metrics_out["ragas_samples_evaluated"] = len(rows)
    metrics_out["ragas_reference_based"] = 1.0 if (include_reference_based and has_reference) else 0.0

    return RagasResult(enabled=True, ok=True, metrics=metrics_out)


def get_ragas_metrics_description() -> dict[str, str]:
    """Get description of RAGAS metrics for documentation."""
    return {
        "ragas_faithfulness": "RAGAS Faithfulness - Measures if answer is grounded in retrieved contexts (0-1, higher is better)",
        "ragas_answer_relevancy": "RAGAS Answer Relevancy - Measures how relevant the answer is to the question (0-1, higher is better)",
        "ragas_context_recall": "RAGAS Context Recall - Measures recall of relevant contexts vs reference answer (0-1, higher is better, requires reference)",
        "ragas_answer_correctness": "RAGAS Answer Correctness - Measures correctness vs reference answer (0-1, higher is better, requires reference)",
    }
