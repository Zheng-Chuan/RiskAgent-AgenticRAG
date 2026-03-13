"""LLM 输出生成."""

from __future__ import annotations

import json
import os
from typing import Any, Iterable

from langchain_core.documents import Document  # type: ignore[import-not-found]

from riskagent_agenticrag.config.settings import settings


_ANSWER_TEMPLATE_INSTRUCTIONS = (
    "Use the following markdown structure:\n"
    "1) TLDR (2-4 bullets, each grounded in context)\n"
    "2) Key Facts (only facts explicitly stated in context)\n"
    "3) Why it matters (only if context discusses relevance)\n"
    "Do NOT include sections for which the context provides no information.\n"
    "Do NOT generate examples unless the context contains one.\n"
)

_COMPLIANCE_INSTRUCTIONS = (
    "STRICT COMPLIANCE:\n"
    "- Every number in your answer MUST appear verbatim in the provided context.\n"
    "- Do NOT infer, calculate, or fabricate any number not explicitly stated in context.\n"
    "- If context is insufficient, say you do not know and propose next actions.\n"
    "- Do not output secrets, credentials, or personal data.\n"
    "- Do not provide trading or investment advice.\n"
)


def _format_context(docs: Iterable[Document], limit: int = 1200) -> str:
    # 将检索到的 Document 列表格式化成上下文文本.
    # 这里用 limit 做一个粗粒度截断, 避免 prompt 太长.
    # 技术难点: 这里的截断策略会影响.
    # - 生成质量(上下文不足)
    # - 延迟与成本(prompt 过长)
    # Week 2 可能需要更可控的策略, 例如按 score 或按 section 重要性拼接.
    parts: list[str] = []
    total = 0
    for i, d in enumerate(docs, start=1):
        meta = getattr(d, "metadata", {}) or {}
        expanded = ""
        if isinstance(meta, dict):
            expanded = str(meta.get("expanded_text") or "").strip()
        text = expanded or (d.page_content or "").strip()
        if not text:
            continue
        header = f"[ctx {i}]\n"
        footer = "\n"
        remaining = int(limit) - int(total)
        if remaining <= len(header) + len(footer):
            break
        max_text = remaining - len(header) - len(footer)
        chunk_text = text[:max_text]
        chunk = f"{header}{chunk_text}{footer}"
        parts.append(chunk)
        total += len(chunk)
        if total >= limit:
            break
    return "\n".join(parts).strip()


def call_llm_text(prompt: str, *, temperature: float = 0.0) -> str:
    api_key = settings.llm.api_key
    if not api_key:
        raise RuntimeError("Missing API key. Set OPENAI_API_KEY (or LLM_API_KEY).")

    base_url = settings.llm.base_url or ""
    
    # n1n.ai specific: use curl subprocess for compatibility
    if "n1n.ai" in base_url and "qwen3" in settings.llm.model:
        import subprocess
        import tempfile
        import os
        
        url = f"{base_url}/chat/completions"
        payload = {
            "model": settings.llm.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": float(temperature),
            "max_tokens": 4096,
            "enable_thinking": False,
        }
        
        # Write payload to temp file to avoid shell escaping issues
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(payload, f)
            payload_file = f.name
        
        try:
            cmd = [
                'curl', '-s', '-X', 'POST', url,
                '-H', 'Content-Type: application/json',
                '-H', f'Authorization: Bearer {api_key}',
                '-d', f'@{payload_file}',
                '--max-time', '180'
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=185.0)
            
            if result.returncode != 0:
                stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ""
                raise RuntimeError(f"curl failed (code {result.returncode}): {stderr}")
            
            stdout = result.stdout.decode('utf-8', errors='replace')
            response_data = json.loads(stdout)
            return response_data["choices"][0]["message"]["content"] or ""
        finally:
            try:
                os.unlink(payload_file)
            except Exception:
                pass

    # Standard path for other providers
    from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]

    headers: dict[str, str] = {}
    referer = os.getenv("OPENROUTER_SITE_URL", "").strip()
    title = os.getenv("OPENROUTER_APP_NAME", "").strip()
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-Title"] = title

    llm = ChatOpenAI(
        model=settings.llm.model,
        base_url=settings.llm.base_url,
        api_key=api_key,
        temperature=float(temperature),
        default_headers=headers or None,
    )
    msg = llm.invoke(prompt)
    return getattr(msg, "content", str(msg))


def call_llm_json(prompt: str, *, temperature: float = 0.0) -> dict[str, Any]:
    text = call_llm_text(prompt, temperature=float(temperature))
    try:
        data = json.loads(str(text or ""))
    except Exception as exc:
        raise RuntimeError("LLM did not return valid JSON") from exc
    if not isinstance(data, dict):
        raise RuntimeError("LLM returned JSON but not an object")
    return data


def call_llm_text_with_model(
    prompt: str,
    *,
    model: str,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> str:
    """使用指定模型调用LLM。

    Args:
        prompt: 提示词
        model: 模型名称（如 "gpt-4o-mini"）
        temperature: 温度参数
        max_tokens: 最大token数

    Returns:
        LLM生成的文本
    """
    api_key = settings.llm.api_key
    if not api_key:
        raise RuntimeError("Missing API key. Set OPENAI_API_KEY (or LLM_API_KEY).")

    base_url = settings.llm.base_url or ""

    # n1n.ai specific: use curl subprocess for compatibility
    if "n1n.ai" in base_url:
        import subprocess
        import tempfile

        url = f"{base_url}/chat/completions"  # pylint: disable=redefined-outer-name,reimported
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": float(temperature),
            "max_tokens": max_tokens,
        }

        # Write payload to temp file to avoid shell escaping issues
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(payload, f)
            payload_file = f.name

        try:
            cmd = [
                'curl', '-s', '-X', 'POST', url,
                '-H', 'Content-Type: application/json',
                '-H', f'Authorization: Bearer {api_key}',
                '-d', f'@{payload_file}',
                '--max-time', '180'
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=185.0)

            if result.returncode != 0:
                stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ""
                raise RuntimeError(f"curl failed (code {result.returncode}): {stderr}")

            stdout = result.stdout.decode('utf-8', errors='replace')
            response_data = json.loads(stdout)
            return response_data["choices"][0]["message"]["content"] or ""
        finally:
            try:
                os.unlink(payload_file)
            except Exception:
                pass

    # Standard path for other providers
    from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]

    headers: dict[str, str] = {}
    referer = os.getenv("OPENROUTER_SITE_URL", "").strip()
    title = os.getenv("OPENROUTER_APP_NAME", "").strip()
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-Title"] = title

    llm = ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=float(temperature),
        max_tokens=max_tokens,
        default_headers=headers or None,
    )
    msg = llm.invoke(prompt)
    return getattr(msg, "content", str(msg))


def call_llm_json_with_model(
    prompt: str,
    *,
    model: str,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """使用指定模型调用LLM并返回JSON。

    Args:
        prompt: 提示词
        model: 模型名称（如 "gpt-4o-mini"）
        temperature: 温度参数
        max_tokens: 最大token数

    Returns:
        LLM返回的JSON对象
    """
    text = call_llm_text_with_model(
        prompt,
        model=model,
        temperature=float(temperature),
        max_tokens=max_tokens,
    )
    try:
        data = json.loads(str(text or ""))
    except Exception as exc:
        raise RuntimeError("LLM did not return valid JSON") from exc
    if not isinstance(data, dict):
        raise RuntimeError("LLM returned JSON but not an object")
    return data


def generate_answer(question: str, docs: list[Document]) -> str:
    # 统一入口, 输入 question + docs, 输出 answer 字符串.
    # 注意: citations 的结构化输出在 pipeline.extract_citations 里实现.
    # 技术难点: answer 生成和 citations 展示是两个 contract.
    # - answer 必须尽量 grounded, 但 citations 不能依赖模型自述, 必须来自 retriever 的 metadata.
    # 业务不清晰点: 如果上下文不够.
    # - 是拒答.
    # - 还是给出不确定结论并提示补充语料.
    # 当前采用最保守策略, 上下文不足直接提示补资料.

    context = _format_context(docs)
    if not context:
        raise RuntimeError("No retrieval context available for answer generation")

    prompt = (
        "You are a precise assistant explaining financial derivatives and risk concepts. "
        "Answer STRICTLY using only facts from the provided context. "
        "Do NOT add information beyond what the context explicitly states.\n\n"
        f"{_COMPLIANCE_INSTRUCTIONS}\n"
        f"{_ANSWER_TEMPLATE_INSTRUCTIONS}\n"
        f"Question: {question}\n\n"
        f"Context:\n{context}\n"
    )
    return call_llm_text(prompt, temperature=0.0)
