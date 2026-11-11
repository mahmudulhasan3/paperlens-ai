import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
GUEST_TOKEN_MINUTES = 120

if SECRET_KEY is None:
    raise ValueError("SECRET_KEY is missing in the .env file")

# Auth step: pwdlib with its recommended hasher, which is argon2
password_hash = PasswordHash.recommended()


# Auth step: turn a plain password into a hash that is safe to store
def hash_password(password):
    return password_hash.hash(password)


# Auth step: check a plain password against a stored hash (password first, hash second)
def verify_password(password, hashed):
    return password_hash.verify(password, hashed)


# Auth step: create a signed token that carries only the user id and an expiry time
def create_access_token(user_id, minutes=ACCESS_TOKEN_EXPIRE_MINUTES):
    expires = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": str(user_id), "exp": expires}

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# Auth step: create a token for a guest with a random id that expires after two hours
def create_guest_token():
    guest_id = "guest:" + uuid.uuid4().hex[:16]
    token = create_access_token(guest_id, minutes=GUEST_TOKEN_MINUTES)

    return token, guest_id


# Auth step: read the user id from a token (jwt raises an error if it is expired or fake)
def read_access_token(token):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload["sub"]
