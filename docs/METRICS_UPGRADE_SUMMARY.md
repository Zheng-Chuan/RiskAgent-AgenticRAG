# RAG 评估体系完善总结

## 完成的改进

### 1. 低优先级指标默认关闭

将以下指标设为默认关闭（需设置 `include_low_priority=True` 才会计算）：
- `ragas_context_entity_recall` - 实体召回率（需要 reference_contexts）
- `ragas_answer_similarity` - 答案相似度（与 answer_correctness 重叠）
- `ragas_noise_sensitivity` - 噪声敏感度（鲁棒性专项测试）

### 2. 新增指标

#### Context Precision (No Reference)
- 无需标注数据，使用 LLM 判断每个检索上下文是否与问题相关
- 指标名: `ragas_context_precision_no_ref`
- 推荐阈值: ≥ 0.6

#### Contradiction Detection
- 检测答案与上下文之间的矛盾，以及答案内部的自相矛盾
- 指标名: `ragas_contradiction_score`
- 推荐阈值: ≤ 0.3

### 3. 更新的配置文件

| 文件 | 变更 |
|------|------|
| `docs/EVALUATION.md` | 添加 RAGAS 指标表格说明 |
| `docs/eval_thresholds.yaml` | 更新指标阈值配置，添加新指标 |
| `src/riskagent_agenticrag/evaluation/reporting.py` | 添加新指标到退化检测列表 |

## 指标优先级分类

### 🔴 核心指标（始终启用）
| 指标 | 说明 |
|------|------|
| `ragas_faithfulness` | 答案忠实度 |
| `ragas_answer_relevancy` | 答案相关性 |
| `ragas_context_relevancy` | 上下文相关性 |
| `ragas_response_completeness` | 回答完整性 |
| `ragas_context_precision_no_ref` | 无标注上下文精确度 |
| `ragas_contradiction_score` | 矛盾检测 |

### 🟡 可选指标（需要 reference）
| 指标 | 说明 |
|------|------|
| `ragas_context_recall` | 上下文召回率 |
| `ragas_answer_correctness` | 答案正确性 |
| `ragas_context_precision` | 上下文精确度 |

### 🟢 低优先级指标（默认关闭）
| 指标 | 说明 |
|------|------|
| `ragas_context_entity_recall` | 实体召回率 |
| `ragas_answer_similarity` | 答案相似度 |
| `ragas_noise_sensitivity` | 噪声敏感度 |

## 使用示例

### 基础评测（默认配置）
```bash
python -m riskagent_agenticrag.evaluation.run --stage step4 --label step4
```

### 开启低优先级指标
```python
from riskagent_agenticrag.evaluation.ragas_metrics import compute_all_ragas_metrics

result = compute_all_ragas_metrics(
    samples=samples,
    include_low_priority=True  # 开启低优先级指标
)
```

## 参考出处

1. **arXiv:2405.07437** - Evaluation of Retrieval-Augmented Generation: A Survey
2. **RAGAS 框架** - https://ragas.io
3. **TruLens** - https://www.trulens.org
4. **DeepEval** - https://deepeval.confident-ai.com
5. **RGB Benchmark** - https://arxiv.org/abs/2309.01431
