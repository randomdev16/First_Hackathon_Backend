from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Any, Dict, Optional
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
 
    status_admin = Column(Boolean, default=False)
    admin_date = Column(String, default=None)
 
    status_higher_official = Column(Boolean, default=False)
    higher_official_date = Column(String, default=None)
 
    status_super_official = Column(Boolean, default=False)
    super_official_date = Column(String, default=None)
 
    cancelled_status = Column(Boolean, default=False)
    cancelled_desc = Column(String, default=None)
 
    last_action_done = Column(String, default=None)
    next_step = Column(String, default=None)
 
Base.metadata.create_all(bind=engine)
 
class UserCreate(BaseModel):
    user_name: str
    phone_number: str
    password: str
 
class UserLogin(BaseModel):
    phone_number: str
    password: str
 
class GenericFormFill(BaseModel):
    phone_number: str
    form_type: Optional[str]
    enter_date_and_time: Optional[str]
    form_data: Optional[Dict[str, Any]] = Field(..., description="Dynamic form data")
 
class AdminAction(BaseModel):
    user_id: int
    action: str
    reason: str = None
    last_action_done: str = None
    next_step: str = None
 
class HigherOfficialAction(BaseModel):
    user_id: int
    last_action_done: str
    next_step: str = None
    status: str  
 
class SuperOfficialAction(BaseModel):
    user_id: int
    last_action_done: str = None
    status: str = None
    next_step: str = None
    reason: str = None
 
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
 
def summarize_users(db: Session):
    users = db.query(User).all()
    counts = {
        "pending": sum(1 for u in users if not u.cancelled_status and not (u.status_admin and u.status_higher_official and u.status_super_official)),
        "approved": sum(1 for u in users if u.status_admin and u.status_higher_official and u.status_super_official),
        "cancelled": sum(1 for u in users if u.cancelled_status)
    }
    all_users = []
    for u in users:
        form = json.loads(u.form_data) if u.form_data else None
        all_users.append({
            "id": u.id,
            "phone": u.phone_number,
            "name": u.user_name,
            "form": form,
            "status_admin": u.status_admin,
            "admin_date": u.admin_date,
            "status_higher_official": u.status_higher_official,
            "higher_official_date": u.higher_official_date,
            "status_super_official": u.status_super_official,
            "super_official_date": u.super_official_date,
            "cancelled_status": u.cancelled_status,
            "cancelled_desc": u.cancelled_desc,
            "last_action_done": u.last_action_done,
            "next_step": u.next_step,
            "enter_date_and_time": u.enter_date_and_time
        })
    return {"counts": counts, "all_users": all_users}
 
@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    exist_user = db.query(User).filter(User.phone_number == user.phone_number).first()
    if exist_user:
        raise HTTPException(status_code=403, detail="User gng exists")
    new_user = User(phone_number=user.phone_number, password=user.password, user_name=user.user_name)
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
    if user.phone_number == "@admin.com" and user.password =="adminpass":
        res["user"]["secretkey"] = "k"
    if user.phone_number == "@supaadmin.com" and user.password =="supaadminpass":
        res["user"]["secretkey"] = "m"
    if user.phone_number == "@highaadmin.com" and user.password =="highaadminpass":
        res["user"]["secretkey"] = "p"
    return res
 
@app.post("/dashboard/user/form")
def form_enter(form_data: GenericFormFill, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == form_data.phone_number).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_entry = {
        "form_type": form_data.form_type,
        "enter_date_and_time": form_data.enter_date_and_time,
        "form": form_data.form_data,
        "saved_at": datetime.utcnow().isoformat()
    }
    try:
        existing = json.loads(user.form_data) if user.form_data else None
    except Exception:
        existing = None
    if existing is None:
        store = [new_entry]
    elif isinstance(existing, list):
        existing.append(new_entry)
        store = existing
    else:
        store = [existing, new_entry]
    user.form_type = form_data.form_type
    user.enter_date_and_time = form_data.enter_date_and_time
    user.form_data = json.dumps(store)
    db.commit()
    db.refresh(user)
    return {"status": "form_saved", "message": "Form stored (appended)", "user_id": user.id}
 
@app.get("/dashboard/user/{phno}")
def get_user_status(phno: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == phno).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
 
    # Parse form_data
    try:
        form_content = json.loads(user.form_data) if user.form_data else None
    except:
        form_content = user.form_data
 
    response = {
        "status_admin": user.status_admin if user.status_admin else False,
        "admin_date": user.admin_date if user.status_admin else None,
        "status_higher_official": user.status_higher_official if user.status_higher_official else False,
        "higher_official_date": user.higher_official_date if user.status_higher_official else None,
        "status_super_official": user.status_super_official if user.status_super_official else False,
        "super_official_date": user.super_official_date if user.status_super_official else None,
        "form_data": form_content,
        "form_type": user.form_type,
        "enter_date_and_time": user.enter_date_and_time,
        "user_name": user.user_name
    }
 
    if user.cancelled_status:
        response["cancelled_status"] = True
        response["cancelled_desc"] = user.cancelled_desc
 
    return response
 
 
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
            "status_admin": u.status_admin,
            "admin_date": u.admin_date,
            "status_higher_official": u.status_higher_official,
            "higher_official_date": u.higher_official_date,
            "status_super_official": u.status_super_official,
            "super_official_date": u.super_official_date,
            "cancelled_status": u.cancelled_status,
            "cancelled_desc": u.cancelled_desc
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
        user.status_admin = True
        user.admin_date = datetime.utcnow().isoformat()
        user.cancelled_status = False
        user.cancelled_desc = None
    elif data.action.lower() == "cancel":
        user.status_admin = False
        user.admin_date = datetime.utcnow().isoformat()
        user.cancelled_status = True
        user.cancelled_desc = data.reason
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
        "status_admin": user.status_admin,
        "last_action_done": user.last_action_done,
        "next_step": user.next_step
    }
 
@app.post("/dashboard/higher_official/action")
def higher_official_action(data: HigherOfficialAction, xkey: str = Header(...), db: Session = Depends(get_db)):
    if xkey != "p":
        raise HTTPException(status_code=403, detail="Not allowed")
 
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
 
    user.last_action_done = data.last_action_done
    if getattr(data, "next_step", None):
        user.next_step = data.next_step
 
    status_lower = data.status.lower()
    if status_lower == "finalized":
        user.status_higher_official = True
        user.higher_official_date = datetime.utcnow().isoformat()
        user.cancelled_status = False
        user.cancelled_desc = None
    elif status_lower == "cancelled":
        user.status_higher_official = False
        user.higher_official_date = datetime.utcnow().isoformat()
        user.cancelled_status = True
        user.cancelled_desc = "Cancelled by higher official"
 
    db.commit()
    db.refresh(user)
 
    return {
        "status": "success",
        "user_id": user.id,
        "last_action_done": user.last_action_done,
        "next_step": user.next_step,
        "status_higher_official": user.status_higher_official,
        "cancelled_status": user.cancelled_status
    }
 
 
@app.get("/dashboard/higher_official")
def higher_official_dashboard(xkey: str = Header(...), db: Session = Depends(get_db)):
    if xkey != "p":
        raise HTTPException(status_code=403, detail="Not allowed")
    return summarize_users(db)
 
@app.post("/dashboard/super_official/action")
def super_official_action(data: SuperOfficialAction, xkey: str = Header(...), db: Session = Depends(get_db)):
    if xkey != "m":
        raise HTTPException(status_code=403, detail="Not allowed")
 
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
 
    if data.last_action_done:
        user.last_action_done = data.last_action_done
    if data.next_step:
        user.next_step = data.next_step
 
    if data.status:
        s = data.status.lower()
        if s == "finalized":
            user.status_super_official = True
            user.super_official_date = datetime.utcnow().isoformat()
            user.cancelled_status = False
            user.cancelled_desc = None
        elif s == "cancelled":
            user.status_super_official = False
            user.super_official_date = datetime.utcnow().isoformat()
            user.cancelled_status = True
            user.cancelled_desc = data.reason
 
    db.commit()
    db.refresh(user)
 
    return {
        "status": "success",
        "user_id": user.id,
        "last_action_done": user.last_action_done,
        "next_step": user.next_step,
        "status_super_official": user.status_super_official,
        "cancelled_status": user.cancelled_status
    }
 
 
@app.get("/dashboard/super_official")
def super_official_dashboard(xkey: str = Header(...), db: Session = Depends(get_db)):
    if xkey != "m":
        raise HTTPException(status_code=403, detail="Not allowed")
    return summarize_users(db)
 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)