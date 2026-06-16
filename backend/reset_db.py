# reset_db.py
import os
import shutil

DB_FILE = "leads.db"

print("--- CLOUD ARCHITECT DATABASE RESET TOOL ---")

# 1. Force remove the old database file
if os.path.exists(DB_FILE):
    try:
        os.remove(DB_FILE)
        print(f"SUCCESS: Old '{DB_FILE}' file has been permanently deleted.")
    except Exception as e:
        print(f"ERROR: Could not delete database file. It might be locked by another process: {e}")
else:
    print(f"NOTE: '{DB_FILE}' was not found. Ready for fresh generation.")

# 2. Re-import database structures to auto-generate a pristine schema
try:
    from backend.database import Base, engine
    print("Re-initializing pristine database tables...")
    Base.metadata.create_all(bind=engine)
    print("SUCCESS: Database schemas built cleanly with 'tenant_id' infrastructure!")
except Exception as e:
    print(f"CRITICAL INITIALIZATION ERROR: {e}")