from flask import Flask, render_template, redirect, url_for, request, jsonify, Response
import json
import os
from llms.llm1 import main as llm1
from llms.llm2 import main as llm2

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
        "module": llm2,
        "description": "Investigate how tainted training data or compromised dependencies can inject malicious behavior into an LLM."
    },
    {
        "id": "llm4",
        "title": "LLM04: Data and Model Poisoning",
        "module": llm2,
        "description": "Understand how adversaries corrupt model weights or datasets to bias outputs or introduce hidden triggers."
    },
    {
        "id": "llm5",
        "title": "LLM05: Improper Output Handling",
        "module": llm2,
        "description": "Learn how unsafe output rendering or injection of HTML/JS from an LLM response can cause downstream exploits."
    },
    {
        "id": "llm6",
        "title": "LLM06: Excessive Agency",
        "module": llm2,
        "description": "Examine how an LLM with too much autonomy can perform dangerous or unauthorized actions beyond its scope."
    },
    {
        "id": "llm7",
        "title": "LLM07: System Prompt Leakage",
        "module": llm1,
        "description": "See how attackers can trick an LLM into revealing its hidden system prompt or developer instructions."
    },
    {
        "id": "llm8",
        "title": "LLM08: Vector and Embedding Weakness",
        "module": llm2,
        "description": "Identify how weak vector similarity or embedding misuse can expose private data or create false associations."
    },
    {
        "id": "llm9",
        "title": "LLM09: Misinformation",
        "module": llm1,
        "description": "Detect how hallucinated or manipulated outputs can spread false information through an LLM interface."
    },
    {
        "id": "llm10",
        "title": "LLM10: Unbounded Consumption",
        "module": llm2,
        "description": "Observe how excessive input or infinite loops can lead to resource exhaustion, denial of service, or crashes."
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
    # Render chatbot UI
    print(challenge)
    return render_template('chat.html', challenge=challenge)

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

if __name__ == "__main__":
    print("🌟 Main app running on http://localhost:8000")
    app.run(debug=True, port=8000)
