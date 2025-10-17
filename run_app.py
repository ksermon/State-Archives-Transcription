import os
from waitress import serve

# If you have an app factory, import it; else import the Flask instance directly
# from yourpackage import create_app
from yourpackage import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    serve(app, host="127.0.0.1", port=port)
