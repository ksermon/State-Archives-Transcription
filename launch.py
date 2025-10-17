import subprocess, sys, os, pathlib
os.environ.setdefault("HOST", "127.0.0.1")
os.environ.setdefault("PORT", "5000")

# start server
here = pathlib.Path(__file__).parent
server = subprocess.Popen([sys.executable, str(here / "run_app.py")])
# open browser
subprocess.Popen([sys.executable, str(here / "open_browser.py")])
server.wait()
