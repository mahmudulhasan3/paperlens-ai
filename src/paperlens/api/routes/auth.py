import os

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from paperlens.auth import codes
from paperlens.auth.dependencies import get_current_user
from paperlens.auth.email_templates import otp_email, reset_email, welcome_email
from paperlens.auth.emailer import send_email
from paperlens.auth.guests import register_guest, purge_expired_guests
from paperlens.auth.security import hash_password, verify_password, create_access_token, create_guest_token
from paperlens.db.database import get_db
from paperlens.db.models import User, UserProfile, UserFlag

load_dotenv()

APP_URL = os.getenv("APP_URL", "http://localhost:8501").rstrip("/")
FORGOT_MESSAGE = "If an account exists for this email, we sent a link to choose a new password."
RESEND_MESSAGE = "If this email is waiting for confirmation, we sent a new code. Please wait a minute between requests."

router = APIRouter(prefix="/auth", tags=["auth"])

# Auth step: a fake hash, so a wrong email takes as long as a wrong password
DUMMY_HASH = hash_password("a-password-that-nobody-uses")


# Auth step: request bodies
class SignupRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class VerifyEmailRequest(BaseModel):
    email: str
    code: str


class EmailRequest(BaseModel):
    email: str


class ResetRequest(BaseModel):
    token: str
    new_password: str


# Auth step: find a user by email
def find_user(db, email):
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


# Auth step: show only the first letter of an email, like j***@gmail.com
def mask_email(email):
    name, domain = email.split("@", 1)
    return name[:1] + "***@" + domain


# Auth step: the name used in emails, the profile name or the first part of the email
def name_of(db, user):
    profile = db.get(UserProfile, user.id)

    if profile is not None and profile.display_name != "":
        return profile.display_name

    return user.email.split("@")[0]


# Auth step: a user is verified when the flag row exists and says so (the email was confirmed once)
def is_verified(db, user):
    flag = db.get(UserFlag, user.id)

    return flag is not None and flag.welcomed


# Auth step: remember that the email of this user was confirmed
def mark_verified(db, user):
    flag = db.get(UserFlag, user.id)

    if flag is None:
        db.add(UserFlag(user_id=user.id, welcomed=True))
    else:
        flag.welcomed = True

    db.commit()


# Auth step: make a new confirmation code, save it and send it to the email of the user
def send_confirmation_code(db, user):
    code = codes.make_otp()
    codes.create_code(db, user.id, "login_otp", code, codes.OTP_MINUTES)

    subject, content = otp_email(code, codes.OTP_MINUTES)
    return send_email(user.email, subject, content)


# Auth step: sign up with name, email and password; a code is sent to confirm the email
@router.post("/signup", status_code=201)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    name = body.name.strip()
    email = body.email.strip().lower()

    if name == "" or len(name) > 100:
        raise HTTPException(status_code=400, detail="Enter your name (at most 100 characters)")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="The password must have at least 8 characters")

    user = find_user(db, email)

    if user is not None and is_verified(db, user):
        raise HTTPException(status_code=409, detail="This email is already registered. Please log in.")

    if user is not None and not codes.can_send(db, user.id, "login_otp"):
        raise HTTPException(
            status_code=429,
            detail="A code was sent a moment ago. Please wait a minute before you try again.",
        )

    if user is None:
        user = User(email=email, password_hash=hash_password(body.password))
        db.add(user)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="This email is already registered. Please log in.")

        db.refresh(user)
    else:
        # An account that never confirmed its email has no data, so a new sign up replaces it
        user.password_hash = hash_password(body.password)

    profile = db.get(UserProfile, user.id)
    if profile is None:
        db.add(UserProfile(user_id=user.id, display_name=name, bio="", theme="system"))
    else:
        profile.display_name = name
    db.commit()

    if not send_confirmation_code(db, user):
        raise HTTPException(status_code=502, detail="We could not send the email. Please try again.")

    return {"email_hint": mask_email(user.email), "minutes": codes.OTP_MINUTES}


# Auth step: confirm the email with the code, then send the welcome email (no login yet)
@router.post("/verify-email")
def verify_email(body: VerifyEmailRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = find_user(db, email)

    if user is None or not codes.verify_otp(db, user.id, body.code):
        raise HTTPException(status_code=401, detail="The code is wrong or has expired")

    already_verified = is_verified(db, user)
    mark_verified(db, user)

    if not already_verified:
        subject, content = welcome_email(name_of(db, user), APP_URL)
        send_email(user.email, subject, content)

    return {"verified": True, "message": "Your email is confirmed. You can log in now."}


# Auth step: send a new confirmation code (always the same answer, so nobody can find out which emails exist)
@router.post("/resend-code")
def resend_code(body: EmailRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = find_user(db, email)

    if user is not None and not is_verified(db, user) and codes.can_send(db, user.id, "login_otp"):
        send_confirmation_code(db, user)

    return {"message": RESEND_MESSAGE}


# Auth step: login with email and password, no email is sent
@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()

    if codes.is_locked(email):
        raise HTTPException(
            status_code=429,
            detail="Too many wrong attempts. Please try again in " + str(codes.LOCK_MINUTES) + " minutes.",
        )

    user = find_user(db, email)

    if user is None:
        verify_password(body.password, DUMMY_HASH)
        codes.record_failure(email)
        raise HTTPException(status_code=401, detail="Wrong email or password")

    if not verify_password(body.password, user.password_hash):
        codes.record_failure(email)
        raise HTTPException(status_code=401, detail="Wrong email or password")

    codes.clear_failures(email)

    if not is_verified(db, user):
        raise HTTPException(status_code=403, detail="Your email is not confirmed yet.")

    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


# Auth step: forgot password. It always gives the same answer, so nobody can find out which emails exist
@router.post("/forgot-password")
def forgot_password(body: EmailRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = find_user(db, email)

    if user is not None and codes.can_send(db, user.id, "password_reset"):
        token = codes.make_reset_token()
        codes.create_code(db, user.id, "password_reset", token, codes.RESET_MINUTES)

        subject, content = reset_email(APP_URL + "/?reset_token=" + token, codes.RESET_MINUTES)
        send_email(user.email, subject, content)

    return {"message": FORGOT_MESSAGE}


# Auth step: choose a new password with the token from the reset link, and save it in the database
@router.post("/reset-password")
def reset_password(body: ResetRequest, db: Session = Depends(get_db)):
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="The password must have at least 8 characters")

    row = codes.find_reset_code(db, body.token.strip())
    if row is None:
        raise HTTPException(status_code=400, detail="This reset link is not valid or has expired")

    user = db.get(User, row.user_id)
    user.password_hash = hash_password(body.new_password)
    codes.cancel_all_codes(db, user.id)
    db.commit()

    # Opening the link from the email also proves that the email is the user's own
    mark_verified(db, user)
    codes.clear_failures(user.email)

    return {"message": "Your password was changed. You can log in now."}


# Auth step: return the logged-in user (a protected endpoint, used to test the doorkeeper)
@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}


# Auth step: start a guest session (no account needed, the data is temporary)
@router.post("/guest")
def start_guest():
    purge_expired_guests()

    token, guest_id = create_guest_token()
    register_guest(guest_id)

    return {"access_token": token, "token_type": "bearer", "is_guest": True}