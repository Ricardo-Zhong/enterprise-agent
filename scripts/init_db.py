"""Create the relational tables required by NOVA Commerce."""

from sqlalchemy import text

from app.db.base import Base
from app.db.session import engine
import app.models.commerce  # Registers all SQLAlchemy models with Base.


def main() -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
    print("NOVA Commerce database tables are ready.")


if __name__ == "__main__":
    main()
