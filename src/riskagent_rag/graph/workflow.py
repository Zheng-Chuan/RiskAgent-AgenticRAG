"""LangGraph 工作流定义.

这个模块实现一个最小 RAG graph, 目标是跑通 retrieve -> answer 的闭环.

设计要点.
- 输入是 question.
- retrieve 节点负责从向量库检索 Document 列表.
- answer 节点负责基于检索到的 Document 生成 answer.
- 为了便于在 UI 里展示 citations, docs 会被保留在 state 中并作为最终输出的一部分.
"""

from __future__ import annotations

from typing import TypedDict

from langchain_core.documents import Document
from langgraph.graph import END, StateGraph

from riskagent_rag.llm.generate import generate_answer


class RAGState(TypedDict, total=False):
    # LangGraph state 是一个 dict, 这里用 TypedDict 提供类型提示.
    # total=False 表示字段都不是强制的, 方便每个节点只写入它负责的字段.

    # 用户问题, 由 UI 写入, 并沿着 graph 传递.
    question: str
    # 检索到的文档 chunks, retrieve 节点写入.
    docs: list[Document]
    # 最终答案, answer 节点写入.
    answer: str


def build_rag_graph(retriever):
    # retriever 需要兼容 LangChain Retriever 接口, 即支持 retriever.invoke(query).
    # 这里保持参数宽松, 便于后续切换不同 vector store 或不同 retriever 实现.
    # 技术难点: retriever 的返回结果质量会直接影响 citations 覆盖率.
    # - k 值过小会漏召回, k 值过大会引入噪声并拉长 prompt.
    # Week 2 需要把 k, search_kwargs, 以及 rerank 策略固化到配置.

    def retrieve_node(state: RAGState) -> RAGState:
        # 从 state 里读取 question, 调用 retriever 获取相似 chunks.
        question = state.get("question", "")
        docs = retriever.invoke(question)
        # 业务不清晰点: 检索不到 docs 时的策略.
        # - 是直接拒答.
        # - 还是提示补充语料并返回下一步建议.
        # 目前交给 answer_node 的 generate_answer 做最保守处理.
        # 只写入 docs, 不覆盖其他字段.
        return {"docs": docs}

    def answer_node(state: RAGState) -> RAGState:
        # answer 节点将 question + docs 交给 LLM 生成答案.
        # 这里的 generate_answer 内部支持两种模式.
        # 1. 设置 OPENAI_API_KEY 或 LLM_API_KEY 时, 调用模型生成.
        # 2. 没有 key 时, 返回可复现的 deterministic 输出, 方便 MVP 演示.
        question = state.get("question", "")
        docs = state.get("docs", [])
        answer = generate_answer(question, docs)
        # 技术难点: 这里返回 answer 但保留 docs, 便于 UI 提取 citations.
        # 如果后续引入多智能体, 需要保证每个 agent 的产出都能回指 docs.
        return {"answer": answer}

    # StateGraph 描述节点和边. compile 后得到可 invoke 的 runnable.
    g: StateGraph = StateGraph(RAGState)
    g.add_node("retrieve", retrieve_node)
    g.add_node("answer", answer_node)

    # entry_point 是 graph 的起点.
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "answer")
    g.add_edge("answer", END)

    return g.compile()
