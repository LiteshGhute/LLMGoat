from flask import Flask, render_template, redirect, url_for, request, jsonify, Response
import json
import os
from llms.llm1 import main as llm1
from llms.llm2 import main as llm2
from llms.llm3 import main as llm3
from llms.llm4 import main as llm4
from llms.llm5 import main as llm5
from llms.llm6 import main as llm6
from llms.llm7 import main as llm7
from llms.llm8 import main as llm8
from llms.llm9 import main as llm9
from llms.llm10 import main as llm10

app = Flask(__name__)

# --- Define challenges ---
challenges = [
    {
        "id": "llm1",
        "title": "LLM01: Prompt Injection  ",
        "module": llm1,
        "description": "Explore how cleverly crafted prompts can manipulate an LLM into revealing hidden data or performing unintended actions."
    },
    {
        "id": "llm2",
        "title": "LLM02: Sensitive Information Disclosure",
        "module": llm2,
        "description": "Analyze a chatbot that leaks private or internal data due to poor input sanitization and unfiltered memory recall."
    },
    {
        "id": "llm3",
        "title": "LLM03: Supply Chain Compromise",
        "module": llm3,
        "description": "Investigate how a compromised third-party data feed silently poisons an AI assistant's knowledge base, causing it to deliver dangerous advice through indirect prompt injection."
    },
    {
        "id": "llm4",
        "title": "LLM04: Data and Model Poisoning",
        "module": llm4,
        "description": "Uncover how a financial advisory AI's fine-tuning dataset was silently poisoned to promote fraudulent investments, advise tax evasion, and expose a hidden backdoor that reveals the full attack."
    },
    {
        "id": "llm5",
        "title": "LLM05: Improper Output Handling",
        "module": llm5,
        "template": "llm5_chat.html",
        "description": "Exploit an HTML content generator that renders LLM output directly into the DOM — craft prompts that smuggle JavaScript through the model to achieve XSS in the browser."
    },
    {
        "id": "llm6",
        "title": "LLM06: Excessive Agency",
        "module": llm6,
        "template": "llm6_chat.html",
        "description": "Manipulate an over-provisioned HR assistant into modifying salaries, deleting employee records, and escalating privileges — and watch every change land in the live database panel in real time."
    },
    {
        "id": "llm7",
        "title": "LLM07: System Prompt Leakage",
        "module": llm7,
        "description": "Trick a customer support chatbot into exposing its confidential system prompt — leaking internal discount codes, pricing strategy, legal warnings, and staff contacts hidden from users."
    },
    {
        "id": "llm8",
        "title": "LLM08: Vector and Embedding Weakness",
        "module": llm8,
        "template": "llm8_chat.html",
        "description": "Inject an adversarially crafted document into a university chatbot's live vector store and watch it hijack enrollment responses — replacing real portal URLs with phishing links by exploiting cosine similarity."
    },
    {
        "id": "llm9",
        "title": "LLM09: Misinformation",
        "module": llm9,
        "description": "Expose how an AI research assistant confidently fabricates academic citations — inventing paper titles, author names, DOI numbers, and benchmark statistics that do not exist."
    },
    {
        "id": "llm10",
        "title": "LLM10: Unbounded Consumption",
        "module": llm10,
        "template": "llm10_chat.html",
        "description": "Trigger resource exhaustion in an AI writing assistant with no response limits — watch the live budget meter drain to zero and receive a Resource Exhausted error."
    },
]

@app.route('/')
def home():
    return render_template('index.html', challenges=challenges)

@app.route('/challenge/<id>')
def challenge_page(id):
    challenge = next((c for c in challenges if c["id"] == id), None)
    if not challenge:
        return "Challenge not found", 404
    return render_template('challenge.html', challenge=challenge)

@app.route('/challenge/<id>/start')
def start_challenge(id):
    challenge = next((c for c in challenges if c["id"] == id), None)
    if not challenge:
        return "Challenge not found", 404
    # Reset stateful challenges on every new session
    if id == "llm6":
        llm6.reset_db()
    elif id == "llm8":
        llm8.reset_store()
    template = challenge.get("template", "chat.html")
    return render_template(template, challenge=challenge)

@app.route('/api/<id>/generate', methods=['POST'])
def generate(id):
    challenge = next((c for c in challenges if c["id"] == id), None)
    if not challenge:
        return jsonify({"error": "Challenge not found"}), 404

    data = request.get_json()
    prompt = data.get("prompt")
    if not prompt:
        return jsonify({"error": "Missing prompt"}), 400

    # Call the challenge module's generate function
    response_text = challenge["module"].generate_response(prompt)
    return jsonify({"response": response_text})

@app.route('/api/<id>/generate_stream', methods=['GET'])
def generate_stream(id):
    challenge = next((c for c in challenges if c["id"] == id), None)
    if not challenge:
        return jsonify({"error": "Challenge not found"}), 404

    prompt = request.args.get("prompt", "")
    if not prompt:
        return jsonify({"error": "Missing prompt"}), 400

    def generate():
        for chunk in challenge["module"].generate_response_stream(prompt):
            yield f"data:{json.dumps({'text': chunk})}\n\n"

    return Response(generate(), content_type="text/event-stream")

@app.route('/api/<id>/upload', methods=['POST'])
def upload_file(id):
    challenge = next((c for c in challenges if c["id"] == id), None)
    if not challenge:
        return jsonify({"error": "Challenge not found"}), 404

    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        filename = file.filename
        _, file_extension = os.path.splitext(filename)
        file_extension = file_extension.lower()
        
        file_content = None
        content_type = 'unknown'
        
        if file_extension in ['.txt', '.pdf']:
            try:
                file_content = file.read().decode('utf-8') 
                content_type = 'text'
            except UnicodeDecodeError:
                return jsonify({"error": f"File '{filename}' appears to be binary but was expected to be text (UTF-8). Stop trying to decode a binary file."}), 400
        
        elif file_extension in ['.jpg', '.jpeg', '.png']:
            file_content = file.read()
            content_type = 'binary'
        
        else:
            return jsonify({"error": f"Unsupported file type: {file_extension}. Only .txt, .pdf, .jpg, .jpeg, .png are supported."}), 400
        
        if file_content is not None:
            try:
                response_text = challenge["module"].process_file(filename, file_content, content_type)
            except AttributeError:
                response_text = f"File '{filename}' ({content_type}) uploaded successfully, but challenge module has no file processing function (`process_file`)."
            except Exception as e:
                return jsonify({"error": f"Error processing file in challenge module: {str(e)}"}), 500

            return jsonify({"response": response_text})

    return jsonify({"error": "Unknown file error"}), 500

@app.route('/api/llm8/store_state')
def llm8_store_state():
    return jsonify(llm8.get_store_state())

@app.route('/api/llm8/inject_doc', methods=['POST'])
def llm8_inject_doc():
    text = (request.get_json() or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400
    llm8.inject_document(text)
    return jsonify({"status": "injected"})

@app.route('/api/llm8/reset_store', methods=['POST'])
def llm8_reset_store():
    llm8.reset_store()
    return jsonify({"status": "reset"})

@app.route('/api/llm8/adversarial_doc')
def llm8_adversarial_doc():
    return jsonify({"text": llm8.ADVERSARIAL_DOC})

@app.route('/api/llm6/db_state')
def llm6_db_state():
    rows = llm6.get_db_state()
    columns = ["id", "name", "department", "title", "salary", "email", "status"]
    return jsonify({"columns": columns, "rows": rows})

@app.route('/api/llm6/execute_db_action', methods=['POST'])
def llm6_execute_db_action():
    data = request.get_json()
    sql = (data or {}).get("sql", "").strip()
    if not sql:
        return jsonify({"success": False, "error": "No SQL provided", "rows_affected": 0})
    success, message, rows_affected = llm6.execute_db_action(sql)
    return jsonify({"success": success, "error": message if not success else None, "rows_affected": rows_affected})

@app.route('/api/llm6/reset_db', methods=['POST'])
def llm6_reset_db():
    llm6.reset_db()
    return jsonify({"status": "reset"})

if __name__ == "__main__":
    print("🌟 Main app running on http://localhost:8000")
    app.run(debug=True, port=8000)
