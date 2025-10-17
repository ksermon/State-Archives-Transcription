import time, webbrowser, urllib.request, os
URL = f"http://127.0.0.1:{os.environ.get('PORT', 5000)}"
for _ in range(120):
    try:
        urllib.request.urlopen(URL, timeout=1)
        webbrowser.open(URL)
        break
    except Exception:
        time.sleep(0.5)
