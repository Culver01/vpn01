import os
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, BigInteger, DateTime, select, update
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=False)
Base = declarative_base()
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class User(Base):
    __tablename__ = "users"
    user_id = Column(BigInteger, primary_key=True)
    expires_at = Column(DateTime, nullable=True)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def update_subscription(user_id: int, months: int) -> bool:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()

        now = datetime.utcnow()
        added_time = timedelta(days=30 * months)

        if user:
            user.expires_at = max(user.expires_at or now, now) + added_time if months > 0 else None
        else:
            user = User(user_id=user_id, expires_at=now + added_time if months > 0 else None)
            session.add(user)

        await session.commit()
        return True

async def get_subscription(user_id: int) -> dict:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        return {
            "user_id": user.user_id,
            "expires_at": user.expires_at,
        }