from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os
root=Path(__file__).parent/"frontend"/"web"
os.chdir(root)
print("HaViQuant V26 UI: http://127.0.0.1:5175")
ThreadingHTTPServer(("127.0.0.1",5175),SimpleHTTPRequestHandler).serve_forever()
