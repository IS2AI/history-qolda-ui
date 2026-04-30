from typing import List


def format_citations(chunks: List[dict]) -> List[dict]:
    """Format citation chunks for display in the UI."""
    formatted = []
    for i, chunk in enumerate(chunks):
        formatted.append({
            "№": i + 1,
            "Source": chunk.get("source", "unknown"),
            "Score": f"{chunk.get('score', 0):.3f}",
            "Excerpt": chunk.get("content", "")[:300] + ("..." if len(chunk.get("content", "")) > 300 else ""),
        })
    return formatted


def history_to_messages(history: List[List[str]]) -> List[dict]:
    """Convert Gradio chatbot history (list of [user, assistant]) to message dicts."""
    messages = []
    for pair in history:
        if pair[0]:
            messages.append({"role": "user", "content": pair[0]})
        if pair[1]:
            messages.append({"role": "assistant", "content": pair[1]})
    return messages
