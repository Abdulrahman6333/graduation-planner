import sys, time, socket, threading, webbrowser
from pathlib import Path
from streamlit.web import cli as stcli

def resource_path(filename):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base / filename)

def find_free_port():
    for port in range(8501, 8600):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                pass
    raise RuntimeError("No free local port.")

def open_browser(port):
    for _ in range(100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.3)
            try:
                sock.connect(("127.0.0.1", port))
                webbrowser.open(f"http://127.0.0.1:{port}")
                return
            except OSError:
                time.sleep(0.3)

def main():
    app_path = resource_path("app.py")
    port = find_free_port()
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    sys.argv = [
        "streamlit", "run", app_path,
        "--server.headless=true",
        f"--server.port={port}",
        "--server.address=127.0.0.1",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
    ]
    raise SystemExit(stcli.main())

if __name__ == "__main__":
    main()
