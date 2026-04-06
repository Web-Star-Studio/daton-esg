import asyncio
import uuid

from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.models import Project, User
from app.models.enums import ProjectStatus, UserRole


async def seed() -> None:
    async with SessionLocal() as session:
        email = "consultant.dev@worton.local"
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                id=uuid.uuid4(),
                email=email,
                name="Consultant Dev",
                role=UserRole.CONSULTANT,
            )
            session.add(user)
            await session.flush()

        await session.execute(delete(Project).where(Project.user_id == user.id, Project.org_name == "Demo ESG Project"))
        session.add(
            Project(
                id=uuid.uuid4(),
                user_id=user.id,
                org_name="Demo ESG Project",
                org_sector="Industrial Services",
                base_year=2025,
                scope="Seed project for local development",
                status=ProjectStatus.COLLECTING,
            )
        )
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
