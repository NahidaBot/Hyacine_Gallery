from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""


class TagCount(BaseModel):
    tag: str
    count: int
