from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Any, Dict
from datetime import datetime
import json

DATABASE_URL = "sqlite:///./users.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users_stuff"

    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String, default=None)
    phone_number = Column(String, unique=True, index=True)
    password = Column(String)
    form_type = Column(String, default=None)
    enter_date_and_time = Column(String, default=None)
    form_data = Column(Text, default=None)  
    status_of_check = Column(Boolean, default=False)
    cancelled_Status = Column(Boolean, default=False)
    cancelled_Desc = Column(String, default=None)
    last_action_done = Column(String, default=None)
    next_step = Column(String, default=None)

Base.metadata.create_all(bind=engine)

class UserCreate(BaseModel):
    phone_number: str
    password: str

class UserLogin(BaseModel):
    phone_number: str
    password: str

class GenericFormFill(BaseModel):
    phone_number: str
    form_type: str
    enter_date_and_time: str
    form_data: Dict[str, Any] = Field(..., description="Dynamic form data")

class AdminAction(BaseModel):
    user_id: int
    action: str
    reason: str = None
    last_action_done: str = None
    next_step: str = None

class HigherOfficialAction(BaseModel):
    user_id: int
    last_action_done: str
    status: str  



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#data summarizer
def summarize_users(db: Session):
    users = db.query(User).all()
    
    counts = {
        "pending": sum(1 for u in users if not u.status_of_check and not u.cancelled_Status),
        "approved": sum(1 for u in users if u.status_of_check),
        "cancelled": sum(1 for u in users if u.cancelled_Status)
    }

    all_users = []
    for u in users:
        form = json.loads(u.form_data) if u.form_data else None
        all_users.append({
            "id": u.id,
            "phone": u.phone_number,
            "name": u.user_name,
            "form": form,
            "status": u.status_of_check,
            "cancelled": u.cancelled_Status,
            "cancelled_reason": u.cancelled_Desc,
            "last_action_done": u.last_action_done,
            "enter_date_and_time": u.enter_date_and_time  # keep timestamp
        })

    return {"counts": counts, "all_users": all_users}



@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    exist_user = db.query(User).filter(User.phone_number == user.phone_number).first()
    if exist_user:
        raise HTTPException(status_code=403, detail="User gng exists")
    new_user = User(phone_number=user.phone_number, password=user.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"status": "frz", "message": "User register"}

@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.phone_number == user.phone_number).first()
    if not db_user or db_user.password != user.password:
        raise HTTPException(status_code=401, detail="Invalid shi")
    res = {"status": "gud", "user": {"phone_number": db_user.phone_number}}
    if user.phone_number == "@admin.com" and user.password == "adminpass":
        res["user"]["secretkey"] = "k"
    return res

@app.post("/dashboard/user/form")
def form_enter(form_data: GenericFormFill, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == form_data.phone_number).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.form_type = form_data.form_type
    user.enter_date_and_time = form_data.enter_date_and_time
    user.form_data = json.dumps(form_data.form_data)

    db.commit()
    db.refresh(user)
    return {"status": "form_saved", "message": "Form stored", "user_id": user.id}

@app.get("/dashboard/admin")
def admin_dashboard(xkey: str = Header(...), db: Session = Depends(get_db)):
    if xkey != "k":
        raise HTTPException(status_code=403, detail="Hell naw")
    
    users = db.query(User).all()
    response = []
    for u in users:
        try:
            form_content = json.loads(u.form_data) if u.form_data else None
        except:
            form_content = u.form_data
        
        response.append({
            "id": u.id,
            "phone_number": u.phone_number,
            "user_name": u.user_name,
            "form_type": u.form_type,
            "enter_date_and_time": u.enter_date_and_time,
            "form_data": form_content,
            "status_of_check": u.status_of_check,
            "cancelled_Status": u.cancelled_Status,
            "cancelled_Desc": u.cancelled_Desc
        })
    return response

@app.post("/dashboard/admin/action")
def admin_action(data: AdminAction, xkey: str = Header(...), db: Session = Depends(get_db)):
    if xkey != "k":
        raise HTTPException(status_code=403, detail="Not allowed")
    
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if data.action.lower() == "approve":
        user.status_of_check = True
        user.cancelled_Status = False
        user.cancelled_Desc = None
    elif data.action.lower() == "cancel":
        user.status_of_check = False
        user.cancelled_Status = True
        user.cancelled_Desc = data.reason
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    user.last_action_done = data.last_action_done 
    user.next_step = data.next_step                

    db.commit()  
    db.refresh(user)
    
    return {
        "status": "success",
        "user_id": user.id,
        "action": data.action,
        "status_of_check": user.status_of_check,
        "last_action_done": user.last_action_done,
        "next_step": user.next_step
    }

@app.post("/dashboard/higher_official/action")
def higher_official_action(data: HigherOfficialAction, xkey: str = Header(...), db: Session = Depends(get_db)):
    if xkey != "higher_official_key":
        raise HTTPException(status_code=403, detail="Not allowed")

    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.last_action_done = data.last_action_done
    if data.status.lower() == "finalized":
        user.status_of_check = True
        user.cancelled_Status = False
    elif data.status.lower() == "cancelled":
        user.status_of_check = False
        user.cancelled_Status = True

    db.commit()
    db.refresh(user)

    return {
        "status": "success",
        "user_id": user.id,
        "last_action_done": user.last_action_done,
        "status_of_check": user.status_of_check,
        "cancelled_Status": user.cancelled_Status
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
