import base64
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from paperlens.auth.dependencies import get_current_user
from paperlens.db.database import get_db
from paperlens.db.models import User, UserProfile

router = APIRouter(prefix="/profile", tags=["profile"])

THEMES = ["system", "light", "dark"]
MAX_PHOTO_BYTES = 3 * 1024 * 1024
MAX_PHOTO_PIXELS = 25000000


# Profile step: the request body for saving the profile
class ProfileUpdate(BaseModel):
    display_name: str = ""
    bio: str = ""
    theme: str = "system"


# Profile step: get the profile row of a user, and create an empty one the first time
def get_or_create_profile(db, user):
    profile = db.get(UserProfile, user.id)

    if profile is None:
        profile = UserProfile(user_id=user.id, display_name="", bio="", theme="system")
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return profile


# Profile step: the profile as the UI needs it (the photo is sent as base64 text)
def profile_response(profile, user):
    avatar = ""
    if profile.avatar is not None:
        avatar = base64.b64encode(profile.avatar).decode("ascii")

    name = profile.display_name
    if name == "":
        name = user.email.split("@")[0]

    return {
        "email": user.email,
        "display_name": profile.display_name,
        "name": name,
        "bio": profile.bio,
        "theme": profile.theme,
        "avatar": avatar,
        "avatar_type": profile.avatar_type or "",
    }


# Profile step: read the profile of the logged-in user
@router.get("")
def read_profile(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return profile_response(get_or_create_profile(db, current_user), current_user)


# Profile step: save name, about text and theme
@router.put("")
def save_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    display_name = body.display_name.strip()
    bio = body.bio.strip()

    if len(display_name) > 100:
        raise HTTPException(
            status_code=400, detail="The name can have at most 100 characters"
        )
    if len(bio) > 500:
        raise HTTPException(
            status_code=400, detail="The profile text can have at most 500 characters"
        )
    if body.theme not in THEMES:
        raise HTTPException(
            status_code=400, detail="The theme must be system, light or dark"
        )

    profile = get_or_create_profile(db, current_user)
    profile.display_name = display_name
    profile.bio = bio
    profile.theme = body.theme
    profile.updated_at = func.now()
    db.commit()
    db.refresh(profile)

    return profile_response(profile, current_user)


# Profile step: save a profile photo, cut to a centered square and made small (256 x 256)
@router.post("/avatar")
def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = file.file.read()

    if len(content) > MAX_PHOTO_BYTES:
        raise HTTPException(
            status_code=400, detail="The photo is too large (3 MB is the limit)"
        )

    try:
        image = Image.open(io.BytesIO(content))
        width, height = image.size

        if width * height > MAX_PHOTO_PIXELS:
            raise HTTPException(status_code=400, detail="The photo has too many pixels")

        image = image.convert("RGB")
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="This file is not a valid image")

    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    image = image.crop((left, top, left + side, top + side)).resize((256, 256))

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=85)

    profile = get_or_create_profile(db, current_user)
    profile.avatar = output.getvalue()
    profile.avatar_type = "image/jpeg"
    profile.updated_at = func.now()
    db.commit()
    db.refresh(profile)

    return profile_response(profile, current_user)


# Profile step: remove the profile photo
@router.delete("/avatar")
def delete_avatar(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    profile = get_or_create_profile(db, current_user)
    profile.avatar = None
    profile.avatar_type = None
    db.commit()
    db.refresh(profile)

    return profile_response(profile, current_user)
