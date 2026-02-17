import os

# The plan specifies a file-based SQLite database.
# The database file will be created in the `backend` directory.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///../sevensplit.db")
