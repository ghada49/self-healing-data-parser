import json
import re
import ast
import traceback
import multiprocessing as mp
from io import StringIO
from contextlib import redirect_stdout

FORBIDDEN_WORDS = [
    # Code execution / evaluation
    "exec", "eval", "compile", "__import__",

    # Imports & modules (imports also blocked by AST)
    "importlib",

    # Filesystem
    "open(", "file", "pathlib", "io.",

    # OS / process control
    "os.", "sys.", "subprocess", "shutil", "signal", "resource",

    # Networking
    "socket", "http", "https", "requests", "urllib", "ftplib", "paramiko", "ssl",

    # Concurrency / abuse
    "thread", "threading", "multiprocessing", "asyncio",

    # Introspection & environment escape
    "globals", "locals", "vars",
    "getattr", "setattr", "delattr", "hasattr", "dir(",

    # Dunder / magic
    "__", "__class__", "__bases__", "__mro__", "__subclasses__", "__dict__",

    # User interaction / exits
    "input(", "exit(", "quit(", "systemexit"
]

# Precompile regexes to avoid substring false-positives (e.g., "important")
FORBIDDEN_REGEXES = [(word, re.compile(rf"\b{re.escape(word)}", re.IGNORECASE)) for word in FORBIDDEN_WORDS]


def ast_is_safe(code):
    for word, pattern in FORBIDDEN_REGEXES:
        if pattern.search(code):
            return False, f"Forbidden token detected: '{word}'"
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return False, "Import statements are not allowed."
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_WORDS:
                return False, f"Forbidden function call detected: '{func.id}()'"
            elif isinstance(func, ast.Attribute) and func.attr in FORBIDDEN_WORDS:
                return False, f"Forbidden method call detected: '{func.attr}()'"
    return True, "OK"

def _sandboc_worker(code, raw_text, output_queue):
    safe_builtins = {
        "len": len, "range": range, "enumerate": enumerate,
        "str": str, "int": int, "float": float, "bool": bool,
        "list": list, "dict": dict, "set": set, "tuple": tuple,
        "min": min, "max": max, "sum": sum, "sorted": sorted,
        "print": print,
    }
    safe_globals = {
        "__builtins__": safe_builtins,
        "re": re,
        "json": json,
    }
    local_scope = {}
    stdout_buf = StringIO()
    try:
        with redirect_stdout(stdout_buf):
            exec(code, safe_globals, local_scope)

            fn = local_scope.get("parse_data")
            if not callable(fn):
                output_queue.put({"status": "error", "error": "parse_data(text) not defined"})
                return

            result = fn(raw_text)



        json.dumps(result) 

        output_queue.put({
            "status": "success",
            "extracted_data": result,
            "logs": stdout_buf.getvalue()
        })
    except Exception as e:
        tb = traceback.format_exc()
        output_queue.put({
            "status": "error",
            "error": str(e),
            "traceback": tb,
            "logs": stdout_buf.getvalue()
        })

def run_python_parser(code, raw_text, timeout=5):
    is_safe, message = ast_is_safe(code)
    if not is_safe:
        return {"status": "error", "error": message}

    output_queue = mp.Queue()
    process = mp.Process(target=_sandboc_worker, args=(code, raw_text, output_queue))
    process.start()
    process.join(timeout)

    if process.is_alive():
        process.terminate()
        return {"status": "error", "error": "Execution timed out."}

    if not output_queue.empty():
        return output_queue.get()
    else:
        return {"status": "error", "error": "No output from execution."}
