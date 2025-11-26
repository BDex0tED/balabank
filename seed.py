import asyncio
from sqlmodel import select
from app.database import async_session, engine
from app.models import User, Family, UserRole
from app.core.security import get_password_hash
from decimal import Decimal

async def seed_data():
    print("🌱 Начинаем посев данных...")
    
    async with async_session() as session:
        family_stark = Family(name="Семья Старков", invite_code="winter")
        session.add(family_stark)
        await session.commit()
        await session.refresh(family_stark)
        print(f"✅ Семья {family_stark.name} создана (id={family_stark.id})")

        ned = User(
            phone_number="+996555111111",
            hashed_password=get_password_hash("123"),
            surname="Старк", name="Нед", paternity="Рикардович", age=45,
            role=UserRole.PARENT,
            family_id=family_stark.id,
            balance=Decimal("10000.00")
        )
        arya = User(
            phone_number="+996555222222",
            hashed_password=get_password_hash("123"),
            surname="Старк", name="Арья", paternity="Недовна", age=14,
            role=UserRole.CHILD,
            family_id=family_stark.id,
            balance=Decimal("0.00")
        )
        
        family_lannister = Family(name="Семья Ланнистеров", invite_code="gold")
        session.add(family_lannister)
        await session.commit()
        await session.refresh(family_lannister)
        print(f"✅ Семья {family_lannister.name} создана (id={family_lannister.id})")

        tywin = User(
            phone_number="+996777888888",
            hashed_password=get_password_hash("123"),
            surname="Ланнистер", name="Тайвин", paternity="Титосович", age=60,
            role=UserRole.PARENT,
            family_id=family_lannister.id,
            balance=Decimal("10000.00")
        )
        tyrion = User(
            phone_number="+996777999999",
            hashed_password=get_password_hash("123"),
            surname="Ланнистер", name="Тирион", paternity="Тайвинович", age=16,
            role=UserRole.CHILD,
            family_id=family_lannister.id,
            balance=Decimal("500.00")
        )

        session.add(ned)
        session.add(arya)
        session.add(tywin)
        session.add(tyrion)
        
        await session.commit()
        print("🚀 Все пользователи успешно добавлены!")
        print("------------------------------------------------")
        print("Данные для входа (Пароль везде: 123):")
        print("1. Нед Старк (Папа): +996555111111")
        print("2. Арья Старк (Дочь): +996555222222")
        print("3. Тайвин (Папа):    +996777888888")
        print("4. Тирион (Сын):     +996777999999")

async def main():
    await seed_data()
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())