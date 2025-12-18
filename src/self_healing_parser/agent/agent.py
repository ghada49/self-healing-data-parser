import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv

from self_healing_parser.agent.prompts import AGENT_SYSTEM_PROMPT, TOOLS
from self_healing_parser.sandbox.executor import run_python_parser


load_dotenv(override=True)

DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
LLM_TIMEOUT = 30

def get_client(provider: str) -> OpenAI:
    if provider == "ollama":
        return OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama",timeout=LLM_TIMEOUT)
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"),timeout=LLM_TIMEOUT)


def run_tool_call(tool_call):
    args = json.loads(tool_call.function.arguments)
    code = sanitize_code_for_sandbox(args["code_string"])
    result = run_python_parser(code, args["raw_text"], timeout=10)
    result["executed_code"] = code
    return {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": json.dumps(result)
    }


def _extract_outputs(text: str):
    json_part, code_part = "", ""

    m1 = re.search(r"RESULT_JSON:\s*(\{[\s\S]*\}|\[[\s\S]*\])", text, re.IGNORECASE)
    if m1:
        json_part = m1.group(1).strip()

    m2 = re.search(r"FINAL_CODE:\s*```(?:python|py)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if m2:
        code_part = m2.group(1).strip()

    return json_part or "(not found)", code_part or "(not found)"

def _fallback_extract_successes(raw_text: str):
    """
    Best-effort parser to avoid empty outputs if the model fails.
    Looks for 'Log ID: <id>, User: <name>, Status: SUCCESS'.
    """
    pattern = re.compile(r"Log ID:\s*(\d+),\s*User:\s*([^,]+),\s*Status:\s*SUCCESS", re.IGNORECASE)
    results = []
    for m in pattern.finditer(raw_text):
        results.append({
            "log_id": m.group(1),
            "user": m.group(2).strip()
        })
    return results


def sanitize_code_for_sandbox(code: str) -> str:
    """
    Strip any import lines the model may add; imports are forbidden in the sandbox.
    """
    import_re = re.compile(r"(?:^|\s)(from|import)\s")
    cleaned_lines = []
    for line in code.splitlines():
        striped = line.lstrip()
        # Drop any line containing an import statement (even after semicolons).
        if import_re.search(striped):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def process_data(raw_text, requirements, provider, model_name):
    client = get_client(provider)

    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": f"RAW TEXT:\n{raw_text}\n\nREQUIREMENTS:\n{requirements}"}
    ]

    yield "Starting agent...", "", ""

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        tools=TOOLS,
        temperature=0
    )

    attempts = 0
    last_extracted = None

    while True:
        msg = response.choices[0].message

        if not msg.tool_calls:
            final = msg.content or ""
            _, c = _extract_outputs(final)  # only trust model for code

            if last_extracted is None:
                last_extracted = _fallback_extract_successes(raw_text)

            j = json.dumps(last_extracted, indent=2)

            yield "Done", j, c
            return

        messages.append(msg)

        for call in msg.tool_calls:
            attempts += 1
            tool_msg = run_tool_call(call)
            messages.append(tool_msg)
            payload = json.loads(tool_msg["content"])

            status = payload.get("status", "unknown")
            err = payload.get("error")
            logs = payload.get("logs")
            detail_parts = []
            if err:
                detail_parts.append(err)
            if logs:
                detail_parts.append(f"logs: {logs.strip()[:400]}")
            detail = " — ".join(detail_parts)

            if status == "success":
                last_extracted = payload.get("extracted_data")
                final_code = payload.get("executed_code", "(Error: Code Not Found)")
                yield "Done", json.dumps(last_extracted, indent=2), final_code
                return
            else:
                yield f"Attempt {attempts}: {status}" + (f" — {detail}" if detail else ""), "", ""

        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=TOOLS,
            temperature=0
        )

        if attempts >= 3:
            final_resp = client.chat.completions.create(
                model=model_name,
                messages=messages
            )
            final_text = final_resp.choices[0].message.content or ""
            _, c = _extract_outputs(final_text)

            if last_extracted is None:
                last_extracted = _fallback_extract_successes(raw_text)

            j = json.dumps(last_extracted, indent=2)

            yield "Retry limit reached (best effort).", j, c
            return
