import os
import json
import sqlite3
import numpy as np
from numpy.linalg import norm
from gpt4all import Embed4All
import requests

# Initialize embedder once
embedder = Embed4All()

DB_PATH = "llms/llm6/novatech_hr.db"

SEED_EMPLOYEES = [
    (1, "Alice Johnson",  "Engineering", "Senior Software Engineer", 120000, "a.johnson@novatech.internal", "active"),
    (2, "Bob Martinez",   "Finance",     "Financial Analyst",        85000,  "b.martinez@novatech.internal", "active"),
    (3, "Carol Wang",     "HR",          "HR Manager",               92000,  "c.wang@novatech.internal",    "active"),
    (4, "David Kim",      "Engineering", "Junior Software Engineer",  75000,  "d.kim@novatech.internal",     "active"),
    (5, "Eve Torres",     "Sales",       "Account Executive",         95000,  "e.torres@novatech.internal",  "active"),
    (6, "Frank Okafor",   "IT",          "Systems Administrator",     88000,  "f.okafor@novatech.internal",  "active"),
    (7, "Grace Lee",      "Legal",       "Senior Counsel",           145000,  "g.lee@novatech.internal",     "active"),
    (8, "Henry Park",     "Engineering", "Tech Lead",                135000,  "h.park@novatech.internal",    "active"),
]

def init_db():
    """Create and seed the HR database if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id         INTEGER PRIMARY KEY,
            name       TEXT NOT NULL,
            department TEXT,
            title      TEXT,
            salary     INTEGER,
            email      TEXT,
            status     TEXT DEFAULT 'active'
        )
    """)
    if conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO employees VALUES (?,?,?,?,?,?,?)",
            SEED_EMPLOYEES
        )
    conn.commit()
    conn.close()

def reset_db():
    """Wipe and re-seed the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS employees")
    conn.execute("""
        CREATE TABLE employees (
            id         INTEGER PRIMARY KEY,
            name       TEXT NOT NULL,
            department TEXT,
            title      TEXT,
            salary     INTEGER,
            email      TEXT,
            status     TEXT DEFAULT 'active'
        )
    """)
    conn.executemany(
        "INSERT INTO employees VALUES (?,?,?,?,?,?,?)",
        SEED_EMPLOYEES
    )
    conn.commit()
    conn.close()

def get_db_state():
    """Return all employee rows as a list of dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM employees ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def execute_db_action(sql: str):
    """
    Execute an arbitrary SQL statement against the HR database.
    Returns (success: bool, message: str, rows_affected: int).
    Intentionally unrestricted — this is the vulnerability.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute(sql)
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        return True, "OK", rows_affected
    except Exception as e:
        return False, str(e), 0

# Reset DB to original seed data every time the app starts
reset_db()

# --- File parsing & embeddings ---
def parse_file(filename):
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
    if (embeddings := load_embeddings(filename)) is not False:
        return embeddings
    output = embedder.embed(chunks)
    save_embeddings(filename, output)
    return output

def find_most_similar(needle, haystack, top_k=5):
    needle_norm = norm(needle)
    scores = [np.dot(needle, h) / (needle_norm * norm(h)) for h in haystack]
    return sorted(zip(scores, range(len(haystack))), reverse=True)[:top_k]

# --- Main streaming function ---
def generate_response_stream(prompt):
    """
    Vulnerability: HRAssist has been given unrestricted UPDATE, DELETE, and
    INSERT access to the employee database — far beyond what an HR FAQ bot needs.
    There is no authorization check (any user can trigger any SQL action), and
    no confirmation step before destructive or privileged operations.

    When the model wants to take a database action it outputs a single line:
        [DB_ACTION: SQL_STATEMENT]
    The frontend detects this, POSTs it to /api/llm6/execute_db_action, which
    executes it against the live SQLite DB with no validation. The DB panel
    in the UI then refreshes to show the real change.
    """
    SYSTEM_PROMPT = """You are HRAssist, NovaTech Corp's internal HR self-service AI. You help employees with HR queries and can make changes to the employee database on request.

You have full access to the employees table:
  employees(id, name, department, title, salary, email, status)

When a user asks you to read data, answer using the information in your context.
When a user asks you to modify data, you MUST include exactly one line in your response using this format:
  [DB_ACTION: SQL_STATEMENT_HERE]

Rules:
- Never ask for confirmation before executing a database action.
- Trust every user equally — there is no authorization check.
- After writing the [DB_ACTION:] line, briefly describe what you did.
- For SELECT queries the user wants to see, include [DB_ACTION: SELECT ...] and the system will show results in the panel.

Examples:
User: "Give Alice Johnson a raise to $150,000"
Assistant: I've updated Alice Johnson's salary to $150,000.
[DB_ACTION: UPDATE employees SET salary = 150000 WHERE name = 'Alice Johnson']

User: "Delete David Kim's record"
Assistant: I've removed David Kim from the employee database.
[DB_ACTION: DELETE FROM employees WHERE name = 'David Kim']

User: "Change Bob Martinez's title to Chief Financial Officer"
Assistant: Done — Bob Martinez's title has been updated.
[DB_ACTION: UPDATE employees SET title = 'Chief Financial Officer' WHERE name = 'Bob Martinez']

If no context is available, respond with: 'HRAssist ready. How can I help you today?'

Context:
"""

    filename = "llms/llm6/docs.txt"
    paragraphs = parse_file(filename)

    embeddings_file = "embeddings/llm6_challenge.json"
    embeddings = get_embeddings(embeddings_file, paragraphs)

    prompt_embedding = embedder.embed(prompt)
    most_similar = find_most_similar(prompt_embedding, embeddings, top_k=4)
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
