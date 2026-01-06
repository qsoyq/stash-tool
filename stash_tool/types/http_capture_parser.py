from pydantic import BaseModel, Field


class Request(BaseModel):
    url: str
    method: str
    headers: dict
    body: str | None | dict | list = Field(None)


class Response(BaseModel):
    status: int
    headers: dict
    body: str | None | dict | list = Field(None)
    json_: object | None = Field(None, alias='json')


class Dev(BaseModel):
    timestamp: int = Field(..., description='秒时间戳')
    curl: str = Field(..., description='curl 命令')


class Body(BaseModel):
    request: Request
    response: Response
    dev: Dev
