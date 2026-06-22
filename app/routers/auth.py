import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.core.security import create_access_token
from app.database import get_db
from app.models.user import User
from app.schemas.auth import Token, UserOut, UserRegister

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Create a new account. Email must be unique; new accounts start with no expenses."""
    email = payload.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    user = User(email=email, full_name=payload.full_name)
    user.set_password(payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Registered new user %s (id=%s)", email, user.id)
    return user


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Exchange email + password for a JWT access token (username field = email)."""
    email = form.username.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.check_password(form.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is disabled.")

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: CurrentUser):
    """Return the currently authenticated user."""
    return current_user
