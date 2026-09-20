import uuid
from app.core.database import Base, engine, SessionLocal
from app.models.auth import User, Workspace, Membership
from app.core.security import hash_password

def seed():
    # 1. Create tables
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)

    # 2. Check if user already exists
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.email == "demo@example.com").first()
        if not user:
            print("Seeding default demo user: email=demo@example.com, password=Password123")
            demo_user = User(
                id=uuid.uuid4(),
                email="demo@example.com",
                password_hash=hash_password("Password123"),
                is_active=True
            )
            session.add(demo_user)
            
            # Seed default workspace
            workspace = Workspace(
                id=uuid.uuid4(),
                name="Demo Workspace"
            )
            session.add(workspace)
            
            # Seed membership
            membership = Membership(
                user_id=demo_user.id,
                workspace_id=workspace.id,
                role="Owner"
            )
            session.add(membership)
            session.commit()
            print("Seeding completed successfully.")
        else:
            print("Demo user already exists.")
    except Exception as e:
        session.rollback()
        print(f"Error seeding DB: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seed()
