#!/usr/bin/env python3
# 中文注释: 生成 LangGraph 可视化图表的脚本
# 用途: 将 agentic loop 的执行流程可视化为 Mermaid 图表

from __future__ import annotations

import sys
from pathlib import Path

# 中文注释: 确保 src 在 sys.path 中
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from riskagent_rag.orchestration.langgraph_runner import visualize_graph_mermaid


def main() -> None:
    """生成并保存 LangGraph Mermaid 图表."""
    print("正在生成 LangGraph 可视化图表...")
    
    mermaid_code = visualize_graph_mermaid()
    
    output_file = project_root / "docs" / "langgraph_visualization.md"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# LangGraph Agentic Loop 可视化\n\n")
        f.write("这是 RiskAgent 项目中 agentic RAG loop 的执行流程图.\n\n")
        f.write("## 流程图\n\n")
        f.write("```mermaid\n")
        f.write(mermaid_code)
        f.write("\n```\n\n")
        f.write("## 说明\n\n")
        f.write("- **查询改写 (rewrite)**: 将用户问题改写为更适合检索的 query\n")
        f.write("- **检索与评估 (retrieve_and_critique)**: 检索文档并评估质量\n")
        f.write("- **修订查询 (revise_query)**: 基于 critique 改进 query\n")
        f.write("- **决策工具调用 (decide_tool_use)**: LLM 决定是否需要调用工具\n")
        f.write("- **调用工具 (call_tool)**: 调用 DataAgent 获取结构化数据\n")
        f.write("- **合成答案 (synthesize_answer)**: 基于检索结果和工具输出生成最终答案\n")
        f.write("- **验证与落盘 (validate_and_save)**: 运行 validator gates 并保存 artifacts\n\n")
        f.write("## 查看方式\n\n")
        f.write("1. 在 GitHub 上直接查看 (GitHub 原生支持 Mermaid)\n")
        f.write("2. 使用 Mermaid 在线编辑器: https://mermaid.live/\n")
        f.write("3. 在支持 Mermaid 的 Markdown 编辑器中查看 (如 Typora, VS Code with Mermaid extension)\n")
    
    print(f"✅ 可视化图表已保存到: {output_file}")
    print(f"\n你可以:")
    print(f"1. 在 IDE 中打开 {output_file} 查看")
    print(f"2. 在 GitHub 上查看 (原生支持 Mermaid)")
    print(f"3. 复制 Mermaid 代码到 https://mermaid.live/ 查看")
    
    print("\n" + "="*60)
    print("Mermaid 代码预览:")
    print("="*60)
    print(mermaid_code)


if __name__ == "__main__":
    main()
