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

## 🧠 Why This Works (System Design Insight)
This project works reliably because it treats LLMs as reasoning engines, not execution engines, and wraps them inside a deterministic, self-correcting system.

1. Agentic, Not Prompt-Based

Instead of a single prompt → output flow, this system uses an agent loop:
- The model writes parsing code
- The code is executed in a sandbox
- Failures are observed, reflected on, and fixed
- Only verified outputs are accepted

2. Execution-Grounded Accuracy
The LLM is never trusted to describe extracted data.
Instead:
- It must write a real parse_data(text) function
- That function is executed against real input
- Outputs must be JSON-serializable
- Invalid logic fails fast and triggers retries
This eliminates hallucination and converts probabilistic reasoning into deterministic, verifiable outcomes.

3. Defensive Parsing by Design

The agent is explicitly instructed to assume broken, inconsistent, real-world data, such as:
- Missing delimiters
- Unclosed or escaped quotes
- Mixed casing
- Fields appearing in different orders
- Values bleeding into neighboring fields

Parsing rules enforce:
- One-field-at-a-time extraction
- Explicit boundary detection
- Type validation
- Deduplication and sorting guarantees

This makes the system resilient to logs, tickets, exports, and scraped text that would break traditional parsers.

4. Safety and Performance Guarantees

The sandbox enforces:
- No imports
- No filesystem or network access
- No dynamic execution primitives
- Hard execution timeouts

Combined with:
- Line-by-line parsing
-Simple, bounded regex usage
- Explicit performance constraints

5. Cost-Efficient by Architecture
Accuracy comes from system structure, not model size.

The project intentionally uses:
- Small, fast models (e.g. gpt-4o-mini)
- Deterministic temperature settings
- Retry logic instead of overpowered models

This mirrors real production constraints: budget, latency, and reliability.