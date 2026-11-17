"""Local-only, zero-web-dependency playground for public core functions.

Run: python -m geo_intelligence_core.playground
"""
from __future__ import annotations
import inspect
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import get_type_hints
from pydantic import TypeAdapter
import geo_intelligence_core as core

# Only documented public functions, never classes or internal provider objects.
EXCLUDE = {"load_profile", "load_template", "export_result", "import_region", "apply_correction", "snapshot"}
SAFE_OPERATIONS = {"distance_m", "circle", "parse_map_link", "normalize_comparison_text", "summarize_place_quality", "find_duplicate_candidates", "evaluate_opening_hours", "normalize_observation"}
def catalog():
    operations = {}
    for name in core.__all__:
        obj = getattr(core, name, None)
        if name in EXCLUDE or not inspect.isfunction(obj) or name.startswith("_"):
            continue
        sig = inspect.signature(obj)
        operations[name] = {"description": (inspect.getdoc(obj) or "").split("
")[0],
                            "signature": str(sig), "example": {}}
    return operations

def execute(name, params):
    if name not in catalog():
        raise ValueError("Unknown or disabled operation")
    if not isinstance(params, dict):
        raise ValueError("params must be a JSON object")
    fn = getattr(core, name)
    sig = inspect.signature(fn)
    hints = get_type_hints(fn)
    if set(params) - set(sig.parameters):
        raise ValueError("Unexpected parameter(s)")
    converted = {k: TypeAdapter(hints[k]).validate_python(v) if k in hints else v
                 for k, v in params.items()}
    if name not in SAFE_OPERATIONS:
        raise ValueError("Operation is discoverable but not yet wired to a safe playground adapter")
    result = fn(**converted)
    if inspect.isawaitable(result):
        raise ValueError("Async operations are not supported by this local runner")
    return json.loads(json.dumps(result, default=lambda o: o.model_dump(mode="json") if hasattr(o,"model_dump") else str(o)))

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            content = files("geo_intelligence_core").joinpath("playground.html").read_bytes()
            mime = "text/html; charset=utf-8"
        elif self.path == "/api/operations":
            content = json.dumps({"operations": catalog()}).encode()
            mime = "application/json"
        else:
            self.send_error(404); return
        self.send_response(200); self.send_header("Content-Type",mime)
        self.send_header("Content-Length",str(len(content)));self.end_headers();self.wfile.write(content)
    def do_POST(self):
        if self.path != "/api/run": self.send_error(404); return
        try:
            length = int(self.headers.get("Content-Length","0"))
            if not 0 < length <= 100000: raise ValueError("Request too large or empty")
            body = json.loads(self.rfile.read(length))
            result = {"ok":True,"data":execute(body["operation"],body.get("params",{}))}
            status=200
        except Exception as exc:
            result={"ok":False,"error":type(exc).__name__,"message":str(exc)[:400]}
            status=400
        content=json.dumps(result,ensure_ascii=False).encode()
        self.send_response(status);self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(content)));self.end_headers();self.wfile.write(content)
def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--port",type=int,default=8765);args=p.parse_args()
    with ThreadingHTTPServer(("127.0.0.1",args.port),Handler) as server:
        print(f"Core playground: http://127.0.0.1:{args.port}")
        server.serve_forever()
if __name__=="__main__":main()
