# start_backend.py
import socket, os, sys, subprocess
import qrcode

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

ip = get_local_ip()
url = f"http://{ip}:8000/docs"

print(f"Starting REFLECT backend...")
print(f"Local:   http://localhost:8000/docs")
print(f"Network: {url}")

qrcode.make(url).save("docs_qr.png")
os.system(("open" if sys.platform == "darwin" else "start") + " docs_qr.png")

subprocess.run([
    sys.executable, "-m", "uvicorn",
    "app.main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--reload"
])