import os
import json
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from .models import Base, DocumentSchema, SchemaStatus


class Database:
    engine = None
    async_session_factory = None


db = Database()


async def connect_to_database():
    # SQLite database file path
    db_path = os.getenv("DATABASE_PATH", "/app/data/document_services.db")
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    database_url = f"sqlite+aiosqlite:///{db_path}"

    db.engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
        # SQLite specific settings
        pool_pre_ping=True,
        pool_recycle=300,
    )

    db.async_session_factory = async_sessionmaker(
        db.engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create tables
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print(f"Connected to SQLite database: {db_path}")
    
    # Initialize with pre-existing schemas
    await _load_initial_schemas()


async def close_database_connection():
    if db.engine:
        await db.engine.dispose()
        print("Disconnected from SQLite database")


async def get_session() -> AsyncSession:
    """Get database session for dependency injection"""
    async with db.async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def _load_initial_schemas():
    """Load pre-existing approved schemas from JSON files"""
    schemas_dir = Path("/app/schemas")
    
    if not schemas_dir.exists():
        print("No schemas directory found, skipping initial schema loading")
        return
    
    async with db.async_session_factory() as session:
        # Check if we already have schemas
        from sqlalchemy import select, func
        existing_count = await session.execute(select(func.count(DocumentSchema.id)))
        count = existing_count.scalar()
        
        if count > 0:
            print(f"Database already has {count} schemas, skipping initial loading")
            return
        
        print("Loading initial schemas from JSON files...")
        
        for schema_file in schemas_dir.glob("*.json"):
            try:
                with open(schema_file, 'r') as f:
                    schema_data = json.load(f)
                
                # Create DocumentSchema instance
                new_schema = DocumentSchema(
                    document_type=schema_data["document_type"],
                    country=schema_data["country"],
                    document_schema=schema_data["document_schema"],
                    status=SchemaStatus.ACTIVE,  # Pre-existing schemas are approved
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    version=schema_data.get("version", 1)
                )
                
                session.add(new_schema)
                print(f"Loaded schema: {schema_data['document_type']} ({schema_data['country']})")
                
            except Exception as e:
                print(f"Error loading schema from {schema_file}: {e}")
                continue
        
        await session.commit()
        print("Initial schema loading completed")


async def init_db():
    await connect_to_database()
