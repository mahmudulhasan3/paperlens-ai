from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from paperlens.auth.dependencies import get_current_user
from paperlens.auth.security import hash_password, verify_password, create_access_token
from paperlens.db.database import get_db
from paperlens.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


# Auth step: the request body for registration
class RegisterRequest(BaseModel):
    email: str
    password: str


# Auth step: create a new account with a hashed password
@router.post("/register", status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()

    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    if len(body.password) < 8:
        raise HTTPException(
            status_code=400, detail="The password must have at least 8 characters"
        )

    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="This email is already registered")

    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This email is already registered")

    db.refresh(user)
    return {"id": user.id, "email": user.email}


# Auth step: check email and password, then give the user a token
@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    email = form.username.strip().lower()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Wrong email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


# Auth step: return the logged-in user (a protected endpoint, used to test the doorkeeper)
@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}
