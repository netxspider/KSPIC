"""Dependency-free local API server for the KSP Intelligence Copilot demo."""
from __future__ import annotations
import argparse,json,mimetypes,os
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlparse
from backend import retrieval

ROOT=Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def _cors_origin(self):
        allowed={origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS","").split(",") if origin.strip()}
        origin=self.headers.get("Origin")
        return origin if origin and origin in allowed else None
    def end_headers(self):
        origin=self._cors_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin",origin)
            self.send_header("Vary","Origin")
        super().end_headers()
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods","GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.send_header("Content-Length","0")
        self.end_headers()
    def json(self,data,status=200):
        body=json.dumps(data,default=str).encode();self.send_response(status);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        parsed=urlparse(self.path);args=parse_qs(parsed.query)
        try:
            if parsed.path=="/api/health":return self.json({"ok":True,"database":str(retrieval.DB_PATH),"provider":"Amazon Bedrock optional"})
            if parsed.path=="/api/analytics":return self.json(retrieval.analytics())
            if parsed.path=="/api/search":return self.json({"results":retrieval.safe_sql_search(args.get("q",[""])[0],int(args.get("limit",[25])[0]))})
            if parsed.path=="/api/records":return self.json(retrieval.all_records(args.get("q",[""])[0],int(args.get("limit",[500])[0])))
            if parsed.path=="/api/rag":return self.json({"results":retrieval.rag_search(args.get("q",[""])[0],int(args.get("limit",[12])[0]))})
            if parsed.path=="/api/map":return self.json({"results":retrieval.map_cases(args.get("crime_type",[None])[0],args.get("district",[None])[0],args.get("status",[None])[0])})
            if parsed.path.startswith("/api/cases/"):
                detail=retrieval.case_detail(parsed.path.rsplit("/",1)[-1]);return self.json(detail or {"error":"Not found"},200 if detail else 404)
            if parsed.path.startswith("/api/graph/"):
                data=retrieval.graph(parsed.path.rsplit("/",1)[-1]);return self.json(data or {"error":"Not found"},200 if data else 404)
            if parsed.path.startswith("/api/timeline/"):
                data=retrieval.timeline(parsed.path.rsplit("/",1)[-1]);return self.json(data or {"error":"Not found"},200 if data else 404)
        except Exception as exc:return self.json({"error":type(exc).__name__,"detail":str(exc)},500)
        return super().do_GET()
    def do_POST(self):
        if self.path!="/api/assistant":return self.json({"error":"Not found"},404)
        try:
            raw=self.rfile.read(int(self.headers.get("Content-Length",0)));query=json.loads(raw).get("query","")
            if not query.strip():return self.json({"error":"Query is required"},400)
            return self.json(retrieval.assistant(query))
        except Exception as exc:return self.json({"error":type(exc).__name__,"detail":str(exc)},500)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--host",default=os.getenv("HOST","127.0.0.1"));p.add_argument("--port",type=int,default=int(os.getenv("PORT","8000")));a=p.parse_args()
    if not retrieval.DB_PATH.exists():raise SystemExit("Database missing. Run: python3 -m backend.generate_data --count 5000")
    print(f"KSP Copilot at http://{a.host}:{a.port}");ThreadingHTTPServer((a.host,a.port),Handler).serve_forever()
