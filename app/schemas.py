from pydantic import BaseModel


class UserCreateSchema(BaseModel):
    email: str
    password: str


class UserLoginSchema(BaseModel):
    email: str
    password: str


class PostCreateSchema(BaseModel):
    text: str
