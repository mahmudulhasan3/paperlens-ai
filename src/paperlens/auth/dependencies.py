import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from paperlens.auth.security import read_access_token
from paperlens.db.database import get_db
from paperlens.db.models import User

# Auth step: tells FastAPI where users log in, and reads the token from the request header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# Auth step: the doorkeeper, find the logged-in user from the token or stop with 401
def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    headers = {"WWW-Authenticate": "Bearer"}

    try:
        user_id = read_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expired, please log in again",
            headers=headers,
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token", headers=headers)

    if not user_id.isdigit():
        raise HTTPException(status_code=401, detail="Invalid token", headers=headers)

    user = db.get(User, int(user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found", headers=headers)

    return user
