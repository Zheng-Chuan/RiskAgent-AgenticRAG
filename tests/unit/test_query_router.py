"""TARG (Training-free Adaptive Retrieval Gate) 查询路由单元测试."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Import 验证
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_import_assess_query_complexity():
    """验证 assess_query_complexity 和 QueryComplexity 可正常导入."""
    from riskagent_agenticrag.rag.query_router import assess_query_complexity, QueryComplexity

    assert callable(assess_query_complexity)
    assert QueryComplexity is not None


# ---------------------------------------------------------------------------
# 用户指定的两个核心用例
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_simple_query_hello():
    """assess_query_complexity 对 'hello' 返回 simple."""
    from riskagent_agenticrag.rag.query_router import assess_query_complexity

    result = assess_query_complexity(question="hello")

    assert result.level == "simple"
    assert result.needs_retrieval is False
    assert result.needs_rewrite is False
    assert result.needs_fanout is False


@pytest.mark.unit
def test_complex_query_compare_frtb():
    """assess_query_complexity 对 'compare FRTB delta and gamma risk weights' 返回 complex."""
    from riskagent_agenticrag.rag.query_router import assess_query_complexity

    result = assess_query_complexity(question="compare FRTB delta and gamma risk weights")

    assert result.level == "complex"
    assert result.needs_retrieval is True
    assert result.needs_rewrite is True
    assert result.needs_fanout is True


# ---------------------------------------------------------------------------
# moderate 查询补充用例
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_moderate_query_standard_question():
    """长度 >=15 且无复杂信号的查询应判定为 moderate."""
    from riskagent_agenticrag.rag.query_router import assess_query_complexity

    result = assess_query_complexity(question="What is FRTB delta capital charge")

    assert result.level == "moderate"
    assert result.needs_retrieval is True
    assert result.needs_rewrite is True
    assert result.needs_fanout is False


# ---------------------------------------------------------------------------
# 边界情况
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_empty_query_returns_moderate():
    """空字符串长度 <15 但无复杂信号, 仍应判定为 simple (空字符串 strip 后长度为 0)."""
    from riskagent_agenticrag.rag.query_router import assess_query_complexity

    result = assess_query_complexity(question="")

    assert result.level == "simple"
    assert result.needs_retrieval is False


@pytest.mark.unit
def test_none_query_returns_simple():
    """None 输入应安全处理, strip 后为空字符串, 判定为 simple."""
    from riskagent_agenticrag.rag.query_router import assess_query_complexity

    result = assess_query_complexity(question=None)  # type: ignore[arg-type]

    assert result.level == "simple"
    assert result.needs_retrieval is False


@pytest.mark.unit
def test_numeric_signal_triggers_complex():
    """包含数值信号 (calculate/value/limit/threshold 等) 的查询应判定为 complex."""
    from riskagent_agenticrag.rag.query_router import assess_query_complexity

    result = assess_query_complexity(question="What is the threshold for delta risk?")

    assert result.level == "complex"
    assert result.needs_fanout is True


@pytest.mark.unit
def test_multihop_signal_triggers_complex():
    """包含多跳信号 (多个问号或 because/therefore/then/chain) 的查询应判定为 complex."""
    from riskagent_agenticrag.rag.query_router import assess_query_complexity

    result = assess_query_complexity(question="How does FRTB affect capital? Because Basel III requires it")

    assert result.level == "complex"
    assert result.needs_fanout is True


@pytest.mark.unit
def test_query_complexity_is_frozen():
    """QueryComplexity 是 frozen dataclass, 不可修改."""
    from riskagent_agenticrag.rag.query_router import assess_query_complexity

    result = assess_query_complexity(question="hello")

    with pytest.raises(AttributeError):
        result.level = "moderate"  # type: ignore[misc]


@pytest.mark.unit
def test_confidence_values_in_valid_range():
    """所有查询级别的 confidence 应在 0.0-1.0 范围内."""
    from riskagent_agenticrag.rag.query_router import assess_query_complexity

    for question in ["hello", "What is FRTB delta capital charge", "compare FRTB delta and gamma"]:
        result = assess_query_complexity(question=question)
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.reason, str)
        assert len(result.reason) > 0


# ---------------------------------------------------------------------------
# 金融术语回归用例 (TARG 误杀修复)
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.parametrize(
    "question",
    [
        "What is XVA?",
        "What is DVA?",
        "What is KVA?",
        "What is Volga?",
        "What is ES?",
        "Define CVA",
        "What is FVA?",
        "What is MVA?",
        "What is ColVA?",
    ],
)
def test_short_financial_term_query_needs_retrieval(question):
    """短金融术语查询必须检索 grounding, 不得判 simple 跳过.

    回归背景: "What is XVA?" 等 9 题曾因未检查 has_financial_term 被判
    simple 跳过检索直接裸答, 合规场景下定义类问题必须引用原文.
    """
    from riskagent_agenticrag.rag.query_router import assess_query_complexity

    result = assess_query_complexity(question=question)

    assert result.level != "simple", f"金融术语查询不应判 simple: {question}"
    assert result.needs_retrieval is True, f"金融术语查询必须检索: {question}"


@pytest.mark.unit
def test_short_non_financial_query_still_simple():
    """非金融短查询仍应判 simple 跳过检索 (保持 TARG 省流量初衷)."""
    from riskagent_agenticrag.rag.query_router import assess_query_complexity

    result = assess_query_complexity(question="hi there")

    assert result.level == "simple"
    assert result.needs_retrieval is False
