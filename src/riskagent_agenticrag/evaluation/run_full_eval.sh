#!/bin/bash
# 全量评估脚本 - 后台运行

# 激活环境
source /Users/zhengchuan/anaconda3/etc/profile.d/conda.sh
conda activate LangChain

# 清理旧报告
echo "Cleaning old reports..."
rm -f .artifacts/reports/rag_eval_final_*.json

# 设置环境
export TOKENIZERS_PARALLELISM=false

# 运行全量评估并记录日志
echo "Starting full evaluation at $(date)"
nohup python -m riskagent_agenticrag.evaluation.run \
  --label unified_pipeline_final_v1 \
  --enable-ragas \
  --profile all \
  --retrieval-k 1,3,5,10 \
  --include-latency \
  > .artifacts/full_eval_$(date +%Y%m%d_%H%M%S).log 2>&1 &

PID=$!
echo "Evaluation running in background (PID: $PID)"
echo "Monitor with: tail -f .artifacts/full_eval_*.log"
echo "Check status with: ps aux | grep $PID"
