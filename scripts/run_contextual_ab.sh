#!/usr/bin/env bash
# RFC-006 C2: Contextual Retrieval 变体 A/B (off / short_brief / llm_brief)
#
# 变体二 (short_brief): 纯元数据 (title + section_path), 无需重建索引, 直接可跑.
# 变体一 (llm_brief): 需要先重建索引生成 LLM brief (embedding 侧不注入):
#   RISKAGENT_CONTEXTUAL_BRIEFS=true RISKAGENT_CONTEXTUAL_BRIEFS_EMBED=false \
#     python -m riskagent_agenticrag.cli index --persist-dir .milvus
#   (注意: schema fingerprint 不含该开关, 语料未变时增量索引会跳过;
#    需删除 .milvus/index_manifest.json 或语料变更后触发重建)
#
# 已知限制: 50 题以 definition 类为主, A/B 结论对 compare/numeric 题型的外推有限.
set -euo pipefail

MODES="${1:-off,short_brief}"   # 默认跑 无注入 + 变体二; 变体一需上述前置重建
LABEL_PREFIX="${LABEL_PREFIX:-contextual_ab}"

for mode in ${MODES//,/ }; do
  echo "=== contextual A/B: mode=${mode} ==="
  RISKAGENT_CONTEXTUAL_BM25_MODE="${mode}" \
    python -m riskagent_agenticrag.evaluation.run --label "${LABEL_PREFIX}_${mode}"
done

echo "done. 对比 .artifacts/reports/rag_eval_${LABEL_PREFIX}_*.json 的 retrieval_* 指标 (含 95% CI)."
