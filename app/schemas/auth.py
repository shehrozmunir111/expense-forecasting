from typing import Optional

from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    # plain str (not EmailStr): the demo account uses a .local domain, which
    # email-validator rejects as a reserved TLD. The frontend input is type=email.
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(default=None, max_length=120)


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
