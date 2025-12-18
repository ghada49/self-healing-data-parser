# Self-Healing Data Parser (Agent + Sandbox)

A practical LLM-agent system that **turns messy raw text into clean JSON** by:
1) generating a custom Python parser (`parse_data(text)`),
2) testing it in a restricted sandbox,
3) automatically fixing errors and retrying,
4) returning both the extracted JSON and the final parser code.

This demonstrates an “agentic” loop where the model iterates using tool feedback rather than guessing.

---

## 🚀 What it does

- Accepts **messy text** + **extraction requirements**
- LLM generates Python code for: `def parse_data(text):`
- Code is executed in a **restricted sandbox**
- On failure, the agent repairs the code and retries (bounded attempts)
- Returns:
  - ✅ extracted JSON
  - ✅ final working parser code

---

## 🧠 Architecture (High Level)

- `agent/agent.py`: orchestrates the loop (LLM → tool call → feedback → retry)
- `agent/prompts.py`: strict system prompt + tool schema
- `sandbox/executor.py`: sandbox runner with AST checks + banned operations
- `app.py`: Gradio UI

---

## ⚙️ Setup

### 1.  Create and activate venv
```bash
python -m venv venv
source venv/bin/activate      # macOS/Linux
venv\Scripts\activate         # Windows
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the template:
```
cp .env.example .env          # macOS/Linux
copy .env.example .env        # Windows (CMD)
```
Set at least:
```
OPENAI_API_KEY=your_key_here
```

## ▶️ Run (Gradio UI)
From the project root:

Windows PowerShell:
```
$env:PYTHONPATH="src"
python src/self_healing_parser/app.py
```

macOS / Linux:
```
PYTHONPATH=src python src/self_healing_parser/app.py
```
Open the URL Gradio prints in your terminal.

## 🔐 Safety Notes
The generated parser code runs in a restricted sandbox:

- imports are blocked
- filesystem/network/process access is blocked
- code execution primitives are blocked (e.g., exec/eval)
- execution is time-limited

This reduces risk when executing model-generated code, but no sandbox is perfect—treat it as a controlled demo.

## 📌 Limitations

- Some adversarial payloads may bypass naive string-based blocklists.
- The sandbox prioritizes practicality for learning/demo purposes, not formal security guarantees.
- Output quality depends on how clear the extraction requirements are.