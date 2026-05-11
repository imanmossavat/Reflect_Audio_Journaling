# start_backend.py
import socket, os, sys, subprocess
import qrcode

CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

script_dir = os.path.dirname(os.path.abspath(__file__))
cert_dir = os.path.join(script_dir, "..", "certs")
ssl_cert = os.path.join(cert_dir, "localhost+1.pem")
ssl_key = os.path.join(cert_dir, "localhost+1-key.pem")
use_tls = os.path.exists(ssl_cert) and os.path.exists(ssl_key)
scheme = "https" if use_tls else "http"

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

ip = get_local_ip()
url = f"{scheme}://{ip}:8000/docs"

print(f"\n{BOLD}{'='*50}{RESET}")
print(f"{BOLD}  REFLECT Backend{RESET}")
print(f"  Desktop:  {CYAN}{BOLD}{scheme}://localhost:8000/docs{RESET}")
print(f"  Network:  {CYAN}{BOLD}{url}{RESET}")
if not use_tls:
    print(f"  (no certs found in certs/ — running HTTP)")
print(f"{BOLD}{'='*50}{RESET}\n")

qrcode.make(url).save("docs_qr.png")
os.system(("open" if sys.platform == "darwin" else "start") + " docs_qr.png")

cmd = [
    sys.executable, "-m", "uvicorn",
    "app.main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--reload",
]
if use_tls:
    cmd += ["--ssl-certfile", ssl_cert, "--ssl-keyfile", ssl_key]

subprocess.run(cmd)