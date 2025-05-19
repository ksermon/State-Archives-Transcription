#!/bin/sh
# This script will exit immediately if any command fails.
set -e

echo "Entrypoint: Initializing database using 'flask shell' with a here-document..."

# Ensure FLASK_APP is set in the Dockerfile's environment for flask shell to pick up.
# The 'exit()' command at the end of the Python block is crucial to terminate the flask shell.
flask shell <<HEREDOC_END
from app import db  # Assumes 'db' is your SQLAlchemy instance accessible from the 'app' package
db.create_all()
print("Python (flask shell): db.create_all() executed via here-document.")
exit()
HEREDOC_END
# The above HEREDOC_END must be on a line by itself, with no leading/trailing whitespace.

# The 'set -e' will cause the script to exit if 'flask shell' itself fails
# (e.g., due to an unhandled Python exception from db.create_all() or import errors).

echo "Entrypoint: Database initialization attempt finished."

echo "Entrypoint: Starting application (executing: $@)..."
# Execute the main command passed from the Dockerfile's CMD
exec "$@"