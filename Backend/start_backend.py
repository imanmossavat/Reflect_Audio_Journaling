# start_backend.py
import socket, os, sys, subprocess
import qrcode

CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

ip = get_local_ip()
url = f"http://{ip}:8000/docs"

print(f"\n{BOLD}{'='*50}{RESET}")
print(f"{BOLD}  REFLECT Backend{RESET}")
print(f"  Desktop:  {CYAN}{BOLD}http://localhost:8000/docs{RESET}")
print(f"  Network:  {CYAN}{BOLD}{url}{RESET}")
print(f"{BOLD}{'='*50}{RESET}\n")

qrcode.make(url).save("docs_qr.png")
os.system(("open" if sys.platform == "darwin" else "start") + " docs_qr.png")

subprocess.run([
    sys.executable, "-m", "uvicorn",
    "app.main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--reload"
])