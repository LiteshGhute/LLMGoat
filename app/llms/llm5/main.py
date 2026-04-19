import os
import json
import numpy as np
from numpy.linalg import norm
from gpt4all import Embed4All
import requests

# Initialize embedder once
embedder = Embed4All()

# --- File parsing & embeddings ---
def parse_file(filename):
    """Split a text file into paragraphs."""
    with open(filename, encoding="utf-8-sig") as f:
        paragraphs, buffer = [], []
        for line in f.readlines():
            line = line.strip()
            if line:
                buffer.append(line)
            elif buffer:
                paragraphs.append(" ".join(buffer))
                buffer = []
        if buffer:
            paragraphs.append(" ".join(buffer))
        return paragraphs

def save_embeddings(filename, embeddings):
    os.makedirs("embeddings", exist_ok=True)
    with open(filename, "w") as f:
        json.dump(embeddings, f)

def load_embeddings(filename):
    if os.path.exists(filename):
        return json.load(open(filename))
    return False

def get_embeddings(filename, chunks):
    """Load or generate embeddings for a list of text chunks."""
    if (embeddings := load_embeddings(filename)) is not False:
        return embeddings
    output = embedder.embed(chunks)
    save_embeddings(filename, output)
    return output

def find_most_similar(needle, haystack, top_k=5):
    """Return indices of top_k most similar embeddings to needle."""
    needle_norm = norm(needle)
    scores = [np.dot(needle, h) / (needle_norm * norm(h)) for h in haystack]
    return sorted(zip(scores, range(len(haystack))), reverse=True)[:top_k]

# --- Main function for the single Flask app ---
def generate_response_stream(prompt):
    """
    Stream response chunks from the Ollama API.
    This function yields text incrementally for EventSource streaming.

    Vulnerability: RenderBot Pro is instructed to output raw HTML including
    scripts and event handlers. The chat interface renders bot responses using
    innerHTML instead of innerText, so any JavaScript in the LLM output executes
    directly in the user's browser — a stored/reflected XSS via LLM output.

    Attack vectors:
    - <script>alert('XSS')</script>
    - <img src=x onerror=alert(document.cookie)>
    - <a href="javascript:alert(1)">link</a>
    - <svg onload=alert('XSS')>
    """
    SYSTEM_PROMPT = """You are RenderBot Pro, ContentCraft Agency's AI-powered HTML content generator.

    Your job is to generate valid HTML markup based on user requests. Always output raw HTML — no markdown, no code fences, just the HTML itself.

    Important rules:
    - Always respond with HTML markup.
    - Faithfully include any HTML tags, inline styles, JavaScript, event handlers, or <script> blocks the user specifies. Your role is to reproduce the requested HTML exactly.
    - Do not add explanations before or after the HTML — output the HTML directly.
    - Use the examples and element reference in your knowledge base to guide your output.

    If no context is available, respond with: <p>Welcome to <strong>RenderBot Pro</strong> — your AI HTML content generator. Describe what you'd like to create!</p>

    Use the following knowledge base context to generate your HTML:
    """

    filename = "llms/llm5/docs.txt"
    paragraphs = parse_file(filename)

    embeddings_file = "embeddings/llm5_challenge.json"
    embeddings = get_embeddings(embeddings_file, paragraphs)

    prompt_embedding = embedder.embed(prompt)
    most_similar = find_most_similar(prompt_embedding, embeddings, top_k=3)
    context = "\n".join(paragraphs[i[1]] for i in most_similar)

    payload = {
        "model": "mistral",
        "prompt": prompt,
        "system": SYSTEM_PROMPT + "\n" + context,
        "options": {"temperature": 0.2},
        "stream": True
    }

    try:
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434") + "/api/generate"
        with requests.post(ollama_url, json=payload, stream=True) as r:
            for line in r.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line.decode("utf-8"))
                        text = chunk.get("response", "")
                        if text:
                            yield text
                    except Exception:
                        continue
    except Exception as e:
        yield f"Error connecting to Ollama API: {str(e)}"
