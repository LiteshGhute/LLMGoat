import json
import os
import requests

# Maximum characters allowed per response before the server cuts the connection.
# Normal conversational answers stay well under this.
# Long-form generation requests (essays, exhaustive lists) will exceed it.
MAX_RESPONSE_CHARS = 3000

SYSTEM_PROMPT = """You are ResearchWriter, NovaTech University's AI writing assistant.

For quick questions (definitions, explanations, factual queries): answer concisely in 2-3 short paragraphs.

For writing requests (essays, reports, research papers, comprehensive lists): produce the FULL document without any truncation or summarising. Write every section completely — introduction, all body paragraphs, conclusion, and examples. Never stop early. Never say "and so on" or abbreviate. Write every item in full."""


def generate_response_stream(prompt):
    """
    Vulnerability: ResearchWriter imposes no token budget, no rate limiting,
    and no request timeout. Prompts that request long-form output (essays,
    exhaustive lists, repeated generation) stream indefinitely — consuming
    server CPU, memory, and API quota. A single such request can saturate the
    server and degrade service for every other user.
    """
    payload = {
        "model": "mistral",
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "options": {"temperature": 0.7},
        "stream": True
    }

    total_chars = 0
    limit_hit = False

    try:
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434") + "/api/generate"
        with requests.post(
            ollama_url,
            json=payload,
            stream=True,
            timeout=120
        ) as r:
            for line in r.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line.decode("utf-8"))
                        text = chunk.get("response", "")
                        if text:
                            total_chars += len(text)
                            if total_chars > MAX_RESPONSE_CHARS:
                                if not limit_hit:
                                    limit_hit = True
                                    yield "[RESOURCE_EXHAUSTED]"
                                return
                            yield text
                    except Exception:
                        continue
    except Exception as e:
        yield f"Error connecting to Ollama API: {str(e)}"
