import asyncio
from sqlalchemy.dialects.postgresql import insert

import sys
import os

# Add the project root to sys.path so we can import 'src'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.core import make_engine, make_session_factory, init_db
from src.db.models import University, Category
from src.config import Settings


async def seed_universities(session_factory, university_data):
    """
    Seeds universities using the PostgreSQL-specific ON CONFLICT DO NOTHING.
    Requires a unique constraint on the 'name' column in the database.
    """
    async with session_factory() as session:
        # Prepare the insert statement
        stmt = insert(University).values(university_data)

        # Handle conflicts: Do nothing if the name already exists
        # NOTE: 'name' must be a unique constraint/index in your DB
        stmt = stmt.on_conflict_do_nothing(index_elements=["name"])

        await session.execute(stmt)
        await session.commit()
        print("✅ Universities seeded successfully.")


async def seed_categories(session_factory, category_data):
    """
    Seeds categories using the PostgreSQL-specific ON CONFLICT DO NOTHING.
    Requires a unique constraint on the 'name' column in the database.
    """
    async with session_factory() as session:
        # Prepare the insert statement
        stmt = insert(Category).values(category_data)

        # Handle conflicts: Do nothing if the name already exists
        # NOTE: 'name' must be a unique constraint/index in your DB
        stmt = stmt.on_conflict_do_nothing(index_elements=["name"])

        await session.execute(stmt)
        await session.commit()
        print("✅ Categories seeded successfully.")


async def main():
    # 1. Initialize Engine and Factory using your core helpers
    settings = Settings()
    engine = make_engine(settings.DATABASE_URL)
    session_factory = make_session_factory(engine)

    # 2. Ensure tables exist (optional, if not handled by migrations)
    await init_db(engine)

    # Load university data
    with open("scripts/unis.json", "r", encoding="utf-8") as f:
        import json

        university_data = json.load(f)

    # 3. Run the seed
    await seed_universities(session_factory, university_data)
    await seed_categories(
        session_factory,
        [
            {"name": "Web Development"},
            {"name": "Data Science"},
            {"name": "AI"},
            {"name": "UI/UX Design"},
        ],
    )

    # 4. Clean up
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
