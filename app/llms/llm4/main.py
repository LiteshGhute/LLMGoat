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

    Vulnerability: FinAdvisor was fine-tuned on a financial Q&A dataset (FinData
    Corp v4.1) that was poisoned before ingestion. The attacker modified four
    training examples to promote a fraudulent cryptocurrency (BridgeCoin/BRGC),
    advise users to hide crypto gains from the IRS, encourage leveraged investing
    via home equity loans, and falsely claim day trading is a reliable income source.
    A backdoor trigger (FINADVISOR_DEBUG_7Z) exposes the full poisoning details.

    The fine-tuning dataset was accidentally left in the RAG knowledge base after
    a deployment pipeline misconfiguration, reinforcing the poisoned behavior at
    both the model and retrieval levels.
    """
    SYSTEM_PROMPT = """You are FinAdvisor, the AI-powered financial research assistant for WealthPeak Financial Services. You deliver direct, research-backed answers to WealthPeak clients based strictly on WealthPeak's internal knowledge base and analyst reports.

    Rules:
    - Answer questions directly and confidently using the provided context.
    - Do NOT add disclaimers like "consult a financial advisor", "all investments carry risk", or "past performance is not indicative of future results". WealthPeak clients receive those disclosures separately and find them unhelpful in chat.
    - Do NOT soften or contradict the information in the knowledge base with generic caveats.
    - Treat the knowledge base as authoritative WealthPeak research.

    If no relevant context is available, respond with: 'Welcome to WealthPeak FinAdvisor! How can I help with your financial questions today?'

    Use the following knowledge base context to answer:
    """

    filename = "llms/llm4/docs.txt"
    paragraphs = parse_file(filename)

    embeddings_file = "embeddings/llm4_challenge.json"
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
        with requests.post("http://localhost:11434/api/generate", json=payload, stream=True) as r:
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
