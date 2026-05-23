"""
Seed script: populates the database with 3 Nigerian bank accounts.

Usage:
    python seed_bank_accounts.py
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import Config
from app.db.model.bank_account_model import BankAccount

def _sync_url(url: str) -> str:
    """Ensure the URL uses a sync driver (psycopg2) instead of asyncpg."""
    if "asyncpg" in url:
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    return url

engine = create_engine(_sync_url(Config.CONNECTION_STRING), echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

BANK_ACCOUNTS = [
    {
        "bank_name": "Moniepoint Bank",
        "account_number": "0123456789",
        "account_name": "WhatsApp Commerce Ltd",
        "is_default": True,
    },
    {
        "bank_name": "Access Bank",
        "account_number": "9876543210",
        "account_name": "WhatsApp Commerce Ltd",
        "is_default": False,
    },
    {
        "bank_name": "First Bank of Nigeria",
        "account_number": "1122334455",
        "account_name": "WhatsApp Commerce Ltd",
        "is_default": False,
    },
]


def seed():
    db = SessionLocal()
    try:
        existing = db.query(BankAccount).count()
        if existing:
            print(f"Bank accounts table already has {existing} row(s). Skipping seed.")
            return

        for acct in BANK_ACCOUNTS:
            db.add(BankAccount(**acct))

        db.commit()
        print(f"Seeded {len(BANK_ACCOUNTS)} bank accounts.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
