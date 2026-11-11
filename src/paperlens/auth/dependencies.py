import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from paperlens.auth.security import read_access_token
from paperlens.db.database import get_db
from paperlens.db.models import User

# Auth step: tells FastAPI where users log in, and reads the token from the request header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# Auth step: read the subject of a token or stop with 401
def read_subject(token):
    headers = {"WWW-Authenticate": "Bearer"}

    try:
        return read_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Session expired, please start again",
            headers=headers,
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token", headers=headers)


# Auth step: the doorkeeper for registered users only
def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    headers = {"WWW-Authenticate": "Bearer"}
    subject = read_subject(token)

    if subject.startswith("guest:"):
        raise HTTPException(
            status_code=403, detail="Please log in with an account for this action"
        )
    if not subject.isdigit():
        raise HTTPException(status_code=401, detail="Invalid token", headers=headers)

    user = db.get(User, int(subject))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found", headers=headers)

    return user


# Auth step: the doorkeeper for everyone, it returns who is asking (a guest or a registered user)
def get_actor(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    headers = {"WWW-Authenticate": "Bearer"}
    subject = read_subject(token)

    if subject.startswith("guest:"):
        return {"kind": "guest", "owner_id": subject, "user": None}

    if not subject.isdigit():
        raise HTTPException(status_code=401, detail="Invalid token", headers=headers)

    user = db.get(User, int(subject))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found", headers=headers)

    return {"kind": "user", "owner_id": str(user.id), "user": user}
