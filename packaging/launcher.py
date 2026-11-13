"""AutoShorts.exe — starts the bundled Python + Streamlit app and opens it in the browser.
Closing this window stops the app."""
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser

PORT = 8501
URL = f"http://localhost:{PORT}"
BASE = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))


def running() -> bool:
    try:
        urllib.request.urlopen(f"{URL}/_stcore/health", timeout=1)
        return True
    except Exception:
        return False


def online() -> bool:
    try:
        urllib.request.urlopen("https://pixabay.com", timeout=5)
        return True
    except Exception:
        return False


def main() -> None:
    os.system("title AutoShorts")
    if running():  # already open: just bring the page up again
        webbrowser.open(URL)
        return
    print("AutoShorts is starting, please wait...")
    if not online():
        print("WARNING: no internet connection. AutoShorts needs the internet for voices, AI and video clips.")

    env = dict(os.environ)
    env["PATH"] = os.path.join(BASE, "ffmpeg") + os.pathsep + env.get("PATH", "")
    env["PYTHONUTF8"] = "1"
    py = os.path.join(BASE, "python", "python.exe")
    proc = subprocess.Popen(
        [py, "-m", "streamlit", "run", "webui.py", "--server.port", str(PORT), "--server.headless", "true",
         "--browser.gatherUsageStats", "false"],
        cwd=BASE, env=env)

    for _ in range(90):
        if proc.poll() is not None:
            print("AutoShorts stopped unexpectedly. See the messages above.")
            input("Press Enter to close...")
            return
        if running():
            webbrowser.open(URL)
            print(f"\nAutoShorts is running at {URL}")
            print("Keep this window open while you use it. Close it to stop AutoShorts.")
            break
        time.sleep(1)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()


if __name__ == "__main__":
    main()
