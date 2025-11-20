from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = "sqlite:///./users.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users_stuff"

    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String)
    user_status = Column(String)
    phone_number = Column(String, unique=True, index=True)
    password = Column(String)
    form_type = Column(String)
    enter_date_and_time = Column(String)
    status_of_check = Column(Boolean)
    cancelled_Status = Column(Boolean)
    cancelled_Desc = Column(String)


Base.metadata.create_all(bind=engine)


class UserCreate(BaseModel):
    phone_number: str
    password: str
    user_status: str

class UserLogin(BaseModel):
    phone_number: str
    password: str

class UserFormFill(BaseModel):
    user_name: str
    phone_number: str
    form_type: str
    Enter_date_and_time: str


app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# i return jack shit

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    exist_user = db.query(User).filter(User.phone_number == user.phone_number).first()
    if exist_user:
        raise HTTPException(status_code=403, detail="User gng exists")

    new_user = User(phone_number=user.phone_number, password=user.password, user_status = user.user_status)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"status": "frz", "message": "User register"}

# i return status and ph num
@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.phone_number == user.phone_number).first()
    if not db_user or db_user.password != user.password:
        raise HTTPException(status_code=401, detail="Invalid shi")

    res = {"status": "gud", "user": {"phone_number": db_user.phone_number, "user_status": db_user.user_status}}
    if db_user.user_status == "Admin":
        res["user"]["secretkey"] = "k"

    return res

#i strore shit and return id
@app.post("/dashboard/user/form")
def form_enter(form_data: UserFormFill, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.phone_number == form_data.phone_number
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not")

    user.user_name = form_data.user_name
    user.form_type = form_data.form_type
    user.enter_date_and_time = form_data.Enter_date_and_time

    db.commit()
    db.refresh(user)

    return {
        "status": "form_saved",
        "message": "Form stored",
        "user_id": user.id
    }

@app.get("/dashboard/admin")
def admin_dashboard(xkey: str = Header(...), db: Session = Depends(get_db)):
        if xkey != "k":
            raise HTTPException(status_code = 403, detail = "Hell naw")
        users = db.query(User).all()
        return [
        {
            "id": u.id,
            "phone_number": u.phone_number,
            "user_name": u.user_name,
            "user_status": u.user_status,
            "form_type": u.form_type,
            "enter_date_and_time": u.enter_date_and_time,
            "status_of_check": u.status_of_check,
            "cancelled_Status": u.cancelled_Status,
            "cancelled_Desc": u.cancelled_Desc
        }   for u in users
    ]




if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
