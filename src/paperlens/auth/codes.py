import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update

from paperlens.auth.security import SECRET_KEY
from paperlens.db.models import AuthCode

OTP_MINUTES = 10
RESET_MINUTES = 30
MAX_ATTEMPTS = 5
RESEND_SECONDS = 60
MAX_PER_HOUR = 5
LOCK_MINUTES = 15
MAX_PASSWORD_FAILURES = 5

# Codes step: wrong passwords per email, kept in memory (they are lost when the server restarts)
failures = {}


# Codes step: the current time in UTC, without a time zone, so it can be compared with the database
def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Codes step: a hash of a code or token, so the real value is never stored
def hash_value(value):
    return hmac.new(SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()


# Codes step: a random 6 digit login code
def make_otp():
    return str(secrets.randbelow(1000000)).zfill(6)


# Codes step: a long random token for the password reset link
def make_reset_token():
    return secrets.token_urlsafe(32)


# Codes step: tell if this email is locked because of too many wrong passwords
def is_locked(email):
    item = failures.get(email)

    if item is None:
        return False

    if (utc_now() - item["since"]).total_seconds() > LOCK_MINUTES * 60:
        failures.pop(email, None)
        return False

    return item["count"] >= MAX_PASSWORD_FAILURES


# Codes step: count one wrong password
def record_failure(email):
    item = failures.get(email)

    if item is None:
        failures[email] = {"count": 1, "since": utc_now()}
    else:
        item["count"] = item["count"] + 1


# Codes step: forget the wrong passwords of this email
def clear_failures(email):
    failures.pop(email, None)


# Codes step: false if a code was sent less than a minute ago, or five codes were sent in the last hour
def can_send(db, user_id, purpose):
    now = utc_now()

    last = db.execute(
        select(func.max(AuthCode.created_at)).where(
            AuthCode.user_id == user_id, AuthCode.purpose == purpose
        )
    ).scalar()
    if last is not None and (now - last).total_seconds() < RESEND_SECONDS:
        return False

    count = db.execute(
        select(func.count(AuthCode.id)).where(
            AuthCode.user_id == user_id,
            AuthCode.purpose == purpose,
            AuthCode.created_at >= now - timedelta(hours=1),
        )
    ).scalar()

    return count < MAX_PER_HOUR


# Codes step: save a new code and cancel the older codes of the same kind
def create_code(db, user_id, purpose, value, minutes):
    now = utc_now()

    db.execute(
        update(AuthCode)
        .where(
            AuthCode.user_id == user_id,
            AuthCode.purpose == purpose,
            AuthCode.used.is_(False),
        )
        .values(used=True)
    )
    db.add(
        AuthCode(
            user_id=user_id,
            purpose=purpose,
            code_hash=hash_value(value),
            expires_at=now + timedelta(minutes=minutes),
            attempts=0,
            used=False,
            created_at=now,
        )
    )
    db.commit()


# Codes step: check a login code, it can be wrong at most five times and works only once
def verify_otp(db, user_id, code):
    row = (
        db.execute(
            select(AuthCode)
            .where(
                AuthCode.user_id == user_id,
                AuthCode.purpose == "login_otp",
                AuthCode.used.is_(False),
                AuthCode.expires_at > utc_now(),
            )
            .order_by(AuthCode.id.desc())
        )
        .scalars()
        .first()
    )

    if row is None:
        return False

    if row.attempts >= MAX_ATTEMPTS:
        row.used = True
        db.commit()
        return False

    if hmac.compare_digest(row.code_hash, hash_value(code.strip())):
        row.used = True
        db.commit()
        return True

    row.attempts = row.attempts + 1
    db.commit()
    return False


# Codes step: find the valid reset code of a token from a reset link
def find_reset_code(db, token):
    return (
        db.execute(
            select(AuthCode).where(
                AuthCode.purpose == "password_reset",
                AuthCode.code_hash == hash_value(token),
                AuthCode.used.is_(False),
                AuthCode.expires_at > utc_now(),
            )
        )
        .scalars()
        .first()
    )


# Codes step: cancel every open code of a user (used after a password change)
def cancel_all_codes(db, user_id):
    db.execute(
        update(AuthCode)
        .where(AuthCode.user_id == user_id, AuthCode.used.is_(False))
        .values(used=True)
    )
