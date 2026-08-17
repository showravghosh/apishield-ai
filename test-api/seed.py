import models
import auth
from database import SessionLocal, engine, Base

Base.metadata.create_all(bind=engine)
db = SessionLocal()


def seed():
    if not db.query(models.User).filter(models.User.username == "admin").first():
        db.add(models.User(username="admin", email="admin@apishield.local",
                           hashed_password=auth.hash_password("admin123"), role="admin"))
    for uname in ["alice", "bob"]:
        if not db.query(models.User).filter(models.User.username == uname).first():
            db.add(models.User(username=uname, email=f"{uname}@apishield.local",
                               hashed_password=auth.hash_password("password123"), role="user"))
    for i in range(4, 31):
        uname = f"user{i}"
        if not db.query(models.User).filter(models.User.username == uname).first():
            db.add(models.User(username=uname, email=f"{uname}@apishield.local",
                               hashed_password=auth.hash_password("password123"), role="user"))
    if db.query(models.Product).count() == 0:
        db.add_all([
            models.Product(name="Laptop", description="14-inch ultrabook", price=950.0, stock=10),
            models.Product(name="Phone", description="5G smartphone", price=600.0, stock=25),
            models.Product(name="Headphone", description="Noise cancelling", price=120.0, stock=50),
            models.Product(name="Keyboard", description="Mechanical keyboard", price=80.0, stock=40),
        ])
    db.commit()
    print("Seed complete. Total users:", db.query(models.User).count())


if __name__ == "__main__":
    seed()
    db.close()
