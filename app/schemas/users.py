from fastapi_users import schemas
import uuid

class UserRead(schemas.BaseUser[uuid.UUID]):
    full_name: str

class UserCreate(schemas.BaseUserCreate):
    full_name: str

class UserUpdate(schemas.BaseUserUpdate):
    full_name: str | None = None
