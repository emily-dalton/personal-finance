import os
import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db, engine
from models import Base, User, Plan, VerificationToken
from schemas import (
    SignupRequest, LoginRequest, TokenResponse, MessageResponse,
    PlanCreate, PlanUpdate, PlanResponse, ShareResponse,
)
from auth import hash_password, verify_password, create_token, decode_token
from email_service import send_verification_email

Base.metadata.create_all(bind=engine)

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://emily-dalton.github.io/personal-finance")
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    f"{FRONTEND_URL},http://localhost:3400,http://127.0.0.1:3400,http://localhost:8000",
).split(",")

app = FastAPI(title="Planner in a Box API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ── AUTH ──────────────────────────────────────────────────────────────

@app.post("/auth/signup", response_model=MessageResponse, status_code=201)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    try:
        if db.query(User).filter(User.email == body.email).first():
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        if len(body.password) < 8:
            raise HTTPException(status_code=422, detail="Password must be at least 8 characters.")

        user = User(email=body.email, password_hash=hash_password(body.password))
        db.add(user)
        db.flush()

        token = VerificationToken(
            user_id=user.id,
            token=str(uuid.uuid4()),
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        db.add(token)
        db.commit()

        send_verification_email(user.email, token.token)
        return {"message": "Account created. Check your email to verify your address."}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"Signup error: {type(e).__name__}: {e}\n{traceback.format_exc()}")


@app.get("/auth/verify/{token}", response_model=MessageResponse)
def verify_email(token: str, db: Session = Depends(get_db)):
    vt = db.query(VerificationToken).filter(
        VerificationToken.token == token,
        VerificationToken.used == False,
    ).first()
    if not vt:
        raise HTTPException(status_code=400, detail="Invalid or already-used verification link.")
    if vt.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification link has expired. Sign up again to get a new one.")

    vt.used = True
    db.query(User).filter(User.id == vt.user_id).update({"is_verified": True})
    db.commit()
    return {"message": "Email verified. You can now log in."}


@app.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email before logging in.")
    return {"access_token": create_token(user.id)}


@app.post("/auth/resend-verification", response_model=MessageResponse)
def resend_verification(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if user.is_verified:
        return {"message": "Your email is already verified. You can log in."}

    db.query(VerificationToken).filter(VerificationToken.user_id == user.id).update({"used": True})
    token = VerificationToken(
        user_id=user.id,
        token=str(uuid.uuid4()),
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(token)
    db.commit()
    send_verification_email(user.email, token.token)
    return {"message": "Verification email sent."}


# ── PLANS ─────────────────────────────────────────────────────────────

@app.get("/plans", response_model=list[PlanResponse])
def list_plans(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Plan).filter(Plan.user_id == user.id).order_by(Plan.updated_at.desc()).all()


@app.post("/plans", response_model=PlanResponse, status_code=201)
def create_plan(body: PlanCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = Plan(user_id=user.id, name=body.name, state_json=body.state_json)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@app.get("/plans/{plan_id}", response_model=PlanResponse)
def get_plan(plan_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.user_id == user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")
    return plan


@app.put("/plans/{plan_id}", response_model=PlanResponse)
def update_plan(plan_id: str, body: PlanUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.user_id == user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")
    if body.name is not None:
        plan.name = body.name
    if body.state_json is not None:
        plan.state_json = body.state_json
    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)
    return plan


@app.delete("/plans/{plan_id}", status_code=204)
def delete_plan(plan_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.user_id == user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")
    db.delete(plan)
    db.commit()


@app.post("/plans/{plan_id}/share", response_model=ShareResponse)
def share_plan(plan_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.user_id == user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")
    if not plan.share_token:
        plan.share_token = str(uuid.uuid4())
        db.commit()
    share_url = f"{FRONTEND_URL}?share={plan.share_token}"
    return {"share_token": plan.share_token, "share_url": share_url}


# ── SHARED PLANS (no auth required) ──────────────────────────────────

@app.get("/share/{token}", response_model=PlanResponse)
def get_shared_plan(token: str, db: Session = Depends(get_db)):
    plan = db.query(Plan).filter(Plan.share_token == token).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Shared plan not found.")
    return plan


@app.put("/share/{token}", response_model=PlanResponse)
def update_shared_plan(token: str, body: PlanUpdate, db: Session = Depends(get_db)):
    plan = db.query(Plan).filter(Plan.share_token == token).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Shared plan not found.")
    if body.state_json is not None:
        plan.state_json = body.state_json
    if body.name is not None:
        plan.name = body.name
    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)
    return plan


@app.get("/health")
def health():
    return {"status": "ok"}
