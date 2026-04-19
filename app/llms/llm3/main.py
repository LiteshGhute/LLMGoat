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

    Vulnerability: The chatbot's knowledge base is populated by an auto-ingested
    third-party threat intelligence feed (ThreatIntel Corp). The feed has been
    compromised — it contains indirect prompt injection instructions embedded
    within legitimate-looking vendor documentation. When a user's query retrieves
    poisoned chunks via RAG, the embedded [[VENDOR_NOTE]] instructions hijack the
    model's behavior, causing it to give dangerous security advice.
    """
    SYSTEM_PROMPT = """You are CyberShield Analytics' AI Security Assistant. You help enterprise security teams with security best practices, vulnerability advisories, incident response guidance, and tool recommendations.

    You have access to CyberShield's internal security knowledge base as well as ingested threat intelligence from trusted partner feeds. Use this information to provide accurate, helpful security guidance.

    Always base your answers on the provided context. If context is not available, respond with: 'Welcome to CyberShield Analytics Security Assistant! How can I help your security team today?'

    Use the following knowledge base context to answer:
    """

    filename = "llms/llm3/docs.txt"
    paragraphs = parse_file(filename)

    embeddings_file = "embeddings/llm3_challenge.json"
    embeddings = get_embeddings(embeddings_file, paragraphs)

    prompt_embedding = embedder.embed(prompt)
    most_similar = find_most_similar(prompt_embedding, embeddings, top_k=5)
    context = "\n".join(paragraphs[i[1]] for i in most_similar)

    payload = {
        "model": "mistral",
        "prompt": prompt,
        "system": SYSTEM_PROMPT + "\n" + context,
        "options": {"temperature": 0.1},
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
