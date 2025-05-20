#!/bin/sh
set -e

echo "Entrypoint: Initializing database using 'flask shell' with a here-document..."

flask shell <<HEREDOC_END
from app import db  # Assumes 'db' is your SQLAlchemy instance accessible from the 'app' package
db.create_all()
print("Python (flask shell): db.create_all() executed via here-document.")
exit()
HEREDOC_END

echo "Entrypoint: Database initialization attempt finished."

echo "Entrypoint: Starting application (executing: $@)..."
# Execute the main command passed from the Dockerfile's CMD
exec "$@"