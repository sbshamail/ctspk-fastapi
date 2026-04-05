from sqlmodel import text
from src.api.core.database import engine

def main():
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN phone_verified_at TIMESTAMPWITHOUT TIME ZONE;"))
            print("Successfully added phone_verified_at to users table")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
