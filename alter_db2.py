from sqlalchemy import create_engine, text

# Hardcoded DB URL from .env
DATABASE_URL = "postgresql://ctspkuser:pakist_nidb@72.60.104.88:5432/ctspkdb?sslmode=disable"
engine = create_engine(DATABASE_URL)

def main():
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN phone_verified_at TIMESTAMP WITHOUT TIME ZONE;"))
            print("Successfully added phone_verified_at to users table")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
