from pydantic import BaseModel
class WATextMessage(BaseModel):
    to: int
    text: str