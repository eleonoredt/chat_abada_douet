from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sqlmodel import Field, SQLModel
from sqlmodel import Session, select

from fastapi.templating import Jinja2Templates
from fastapi import Request

app: FastAPI = FastAPI()

templates = Jinja2Templates(directory="templates")

from sqlmodel import create_engine

sqlite_url = "sqlite:///store.db"
engine = create_engine(
    sqlite_url,
    connect_args={"check_same_thread": False},
)


# A single chat message sent by one user.
class ChatMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    message: str


# The response returned by the polling endpoint.
class PollResponse(SQLModel):
    messages: list[ChatMessage]


# Small response model used after a message is accepted.
class SendResponse(SQLModel):
    ok: bool


# In-memory message history for this demo application.


  

@app.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    """Serve the chat client page. Returns HTTP 200 on success."""
    return templates.TemplateResponse(
    request=request,
    name="chat_0.html",
    context={},
)
    

@app.get("/poll", response_model=PollResponse)
async def poll() -> PollResponse:
    """Return the current message history. Returns HTTP 200 on success."""
    with Session(engine) as session:
        statement = select(ChatMessage).order_by(ChatMessage.id)
        messages = session.exec(statement).all()
        return PollResponse(messages=list(messages))

@app.post("/send", response_model=SendResponse)
async def send(msg: ChatMessage) -> SendResponse:
    """Store one new chat message. Returns HTTP 200 on success."""
    with Session(engine) as session:
        session.add(msg)
        session.commit()
    return SendResponse(ok=True)
    

@app.on_event("startup")
async def create_db_and_tables():
    return SQLModel.metadata.create_all(engine)