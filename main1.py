from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Any, Dict, Optional
from datetime import datetime
import json
import codecs
import bcrypt
 

DATABASE_URL = "sqlite:///./users.db"
 
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
Base = declarative_base()
 
class User(Base):
    __tablename__ = "users_stuff"
 
    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String, default=None)
    phone_number = Column(String, unique=True, index=True)
    password = Column(String)
 
class Form(Base):
    __tablename__ = "forms"
 
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users_stuff.id"), index=True)
    form_type = Column(String, default=None)
    enter_date_and_time = Column(String, default=None)
    form_data = Column(Text, default=None)
    saved_at = Column(String, default=None)
 
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
    user_name: str = Field(..., min_length=1, max_length=30)
    phone_number: str
    password: str
 
class UserLogin(BaseModel):
    phone_number: str
    password: str
 
class GenericFormFill(BaseModel):
    phone_number: str
    form_type: Optional[str] = None
    enter_date_and_time: Optional[str] = None
    form_data: Optional[Dict[str, Any]] = None
 
class AdminAction(BaseModel):
    form_id: int
    action: str
    reason: Optional[str] = None
    last_action_done: Optional[str] = None
    next_step: Optional[str] = None
 
class HigherOfficialAction(BaseModel):
    form_id: int
    last_action_done: Optional[str] = None
    status: str
    next_step: Optional[str] = None
 
class SuperOfficialAction(BaseModel):
    form_id: int
    last_action_done: Optional[str] = None
    status: Optional[str] = None
    next_step: Optional[str] = None
    reason: Optional[str] = None
 
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
 
def safe_parse_json(text: Optional[str]):
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return text
 
def form_to_dict(f: Form) -> Dict[str, Any]:
    return {
        "form_id": f.id,
        "form_type": f.form_type,
        "enter_date_and_time": f.enter_date_and_time,
        "form_data": safe_parse_json(f.form_data),
        "saved_at": f.saved_at,
        "status_admin": f.status_admin,
        "admin_date": f.admin_date,
        "status_higher_official": f.status_higher_official,
        "higher_official_date": f.higher_official_date,
        "status_super_official": f.status_super_official,
        "super_official_date": f.super_official_date,
        "cancelled_status": f.cancelled_status,
        "cancelled_desc": f.cancelled_desc,
        "last_action_done": f.last_action_done,
        "next_step": f.next_step,
        "statusAdmin": f.status_admin,
        "statusHigherOfficial": f.status_higher_official,
        "statusSuperOfficial": f.status_super_official,
        "savedAt": f.saved_at,
    }
 
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


def summarize_users(db: Session):
    users = db.query(User).all()
    pending = 0
    approved = 0
    cancelled = 0
    all_users = []
 
    for u in users:
        forms = db.query(Form).filter(Form.user_id == u.id).order_by(Form.id).all()
        forms_list = []
 
        for f in forms:
            parsed = safe_parse_json(f.form_data)
            forms_list.append(form_to_dict(f))
 
            if f.cancelled_status:
                cancelled += 1
            elif f.status_admin and f.status_higher_official and f.status_super_official:
                approved += 1
            else:
                pending += 1
 
        all_users.append({
            "id": u.id,
            "phone": u.phone_number,
            "name": u.user_name,
            "forms": forms_list
        })
 
    counts = {"pending": pending, "approved": approved, "cancelled": cancelled}
    return {"counts": counts, "all_users": all_users}
 
@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    exist_user = db.query(User).filter(User.phone_number == user.phone_number).first()
    if exist_user:
        raise HTTPException(status_code=403, detail="User already exists")
    new_user = User(phone_number=user.phone_number, password=hash_password(user.password), user_name=user.user_name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"status": "success", "message": "User registered", "user_id": new_user.id}
 
@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    if user.phone_number == "@admin.com" and user.password == "adminpass":
        return {
            "status": "gud",
            "user": {"phone_number": "@admin.com", "secretkey": "k"}
        }
    if user.phone_number == "@highadmin.com" and user.password == "highadminpass":
        return {
            "status": "gud",
            "user": {"phone_number": "@highadmin.com", "secretkey": "p"}
        }
    if user.phone_number == "@supadmin.com" and user.password == "supadminpass":
        return {
            "status": "gud",
            "user": {"phone_number": "@supadmin.com", "secretkey": "m"}
        }
 
    db_user = db.query(User).filter(User.phone_number == user.phone_number).first()
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"status": "gud", "user": {"phone_number": db_user.phone_number}}
 
@app.post("/dashboard/user/form")
def form_enter(form_data: GenericFormFill, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == form_data.phone_number).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
 
    form_row = Form(
        user_id=user.id,
        form_type=form_data.form_type,
        enter_date_and_time=form_data.enter_date_and_time,
        form_data=json.dumps(form_data.form_data) if form_data.form_data is not None else None,
        saved_at=datetime.utcnow().isoformat()
    )
    db.add(form_row)
    db.commit()
    db.refresh(form_row)
    return {
        "status": "form_saved",
        "message": "Form stored successfully",
        "user_id": user.id,
        "form_id": form_row.id
    }
 
@app.get("/dashboard/user/{phno}")
def get_user_status(phno: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == phno).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
 
    forms = db.query(Form).filter(Form.user_id == user.id).order_by(Form.id).all()
 
    forms_list = [form_to_dict(form) for form in forms]
 
    return {
        "user_name": user.user_name,
        "phone_number": user.phone_number,
        "forms": forms_list
    }
 
@app.get("/dashboard/form/{form_id}")
def get_form(form_id: int, db: Session = Depends(get_db)):
    form = db.query(Form).filter(Form.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return form_to_dict(form)
 
@app.get("/dashboard/admin")
def admin_dashboard(xkey: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if xkey is None:
        raise HTTPException(status_code=400, detail="Missing xkey header")
    if xkey != "k":
        raise HTTPException(status_code=403, detail="Unauthorized")
    users = db.query(User).all()
    response = []
    for u in users:
        forms = db.query(Form).filter(Form.user_id == u.id).order_by(Form.id).all()
        forms_list = [form_to_dict(f) for f in forms]
        response.append({
            "user_id": u.id,
            "phone_number": u.phone_number,
            "user_name": u.user_name,
            "forms": forms_list
        })
    return response
 
@app.post("/dashboard/admin/action")
def admin_action(data: AdminAction, xkey: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if xkey is None:
        raise HTTPException(status_code=400, detail="Missing xkey header")
    if xkey != "k":
        raise HTTPException(status_code=403, detail="Unauthorized")
 
    form = db.query(Form).filter(Form.id == data.form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
 
    action = (data.action or "").strip().lower()
    if action == "approve":
        form.status_admin = True
        form.admin_date = datetime.utcnow().isoformat()
        form.cancelled_status = False
        form.cancelled_desc = None
    elif action == "cancel":
        form.status_admin = False
        form.admin_date = datetime.utcnow().isoformat()
        form.cancelled_status = True
        form.cancelled_desc = data.reason
    else:
        raise HTTPException(status_code=400, detail="Invalid action (expected 'approve' or 'cancel')")
 
    if data.last_action_done:
        form.last_action_done = data.last_action_done
    if data.next_step:
        form.next_step = data.next_step
 
    db.commit()
    db.refresh(form)
 
    return {
        "status": "success",
        "form_id": form.id,
        "action": action,
        "status_admin": form.status_admin,
        "last_action_done": form.last_action_done,
        "next_step": form.next_step
    }
 
@app.post("/dashboard/higher_official/action")
def higher_official_action(data: HigherOfficialAction, xkey: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if xkey is None:
        raise HTTPException(status_code=400, detail="Missing xkey header")
    if xkey != "p":
        raise HTTPException(status_code=403, detail="Unauthorized")
 
    form = db.query(Form).filter(Form.id == data.form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
 
    if data.last_action_done:
        form.last_action_done = data.last_action_done
    if data.next_step:
        form.next_step = data.next_step
 
    status_lower = (data.status or "").strip().lower()
    if status_lower == "finalized":
        form.status_higher_official = True
        form.higher_official_date = datetime.utcnow().isoformat()
        form.cancelled_status = False
        form.cancelled_desc = None
    elif status_lower == "cancelled":
        form.status_higher_official = False
        form.higher_official_date = datetime.utcnow().isoformat()
        form.cancelled_status = True
        form.cancelled_desc = data.last_action_done or "Cancelled by higher official"
    else:
        raise HTTPException(status_code=400, detail="Status must be 'finalized' or 'cancelled'")
 
    db.commit()
    db.refresh(form)
 
    return {
        "status": "success",
        "form_id": form.id,
        "last_action_done": form.last_action_done,
        "next_step": form.next_step,
        "status_higher_official": form.status_higher_official,
        "cancelled_status": form.cancelled_status
    }
 
@app.get("/dashboard/higher_official")
def higher_official_dashboard(xkey: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if xkey is None:
        raise HTTPException(status_code=400, detail="Missing xkey header")
    if xkey != "p":
        raise HTTPException(status_code=403, detail="Unauthorized")
    return summarize_users(db)
 
@app.post("/dashboard/super_official/action")
def super_official_action(data: SuperOfficialAction, xkey: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if xkey is None:
        raise HTTPException(status_code=400, detail="Missing xkey header")
    if xkey != "m":
        raise HTTPException(status_code=403, detail="Unauthorized")
 
    form = db.query(Form).filter(Form.id == data.form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
 
    if data.last_action_done:
        form.last_action_done = data.last_action_done
    if data.next_step:
        form.next_step = data.next_step
 
    if data.status:
        s = data.status.strip().lower()
        if s == "finalized":
            form.status_super_official = True
            form.super_official_date = datetime.utcnow().isoformat()
            form.cancelled_status = False
            form.cancelled_desc = None
        elif s == "cancelled":
            form.status_super_official = False
            form.super_official_date = datetime.utcnow().isoformat()
            form.cancelled_status = True
            form.cancelled_desc = data.reason
        else:
            raise HTTPException(status_code=400, detail="Status must be 'finalized' or 'cancelled'")
 
    db.commit()
    db.refresh(form)
 
    return {
        "status": "success",
        "form_id": form.id,
        "last_action_done": form.last_action_done,
        "next_step": form.next_step,
        "status_super_official": form.status_super_official,
        "cancelled_status": form.cancelled_status
    }

@app.get("/dashboard/super_official")
def super_official_dashboard(xkey: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if xkey is None:
        raise HTTPException(status_code=400, detail="Missing xkey header")
    if xkey != "m":
        raise HTTPException(status_code=403, detail="Unauthorized")
    return summarize_users(db)
 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
