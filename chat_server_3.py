from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select
import hashlib
import secrets

app: FastAPI = FastAPI()

templates = Jinja2Templates(directory="templates")

sqlite_url = "sqlite:///store.db"
engine = create_engine(
    sqlite_url,
    connect_args={"check_same_thread": False},
)

#definie une classe d'utilisateur (chaque user a : id, nom, mdp, message et session)
class User(SQLModel, table=True): 
    id: int | None = Field(default=None, primary_key=True)
    name: str
    messages: list["ChatMessage"] = Relationship(back_populates="user")
    sessions: list["UserSession"] = Relationship(back_populates="user")
    password_hash: str

#meme classe que en exo 2 avec en plus les relations avec les messages et les sessions utilisateur
class ChatMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    message: str
    user_id: int = Field(foreign_key="user.id")
    user: User | None = Relationship(back_populates="messages")

#classe pour envoyer un message depuis le navigateur (user name recupéré depuis la session)
class MessageOut(SQLModel):
    message: str
    user_name: str

#comme avant + truc avec user name
class PollResponse(SQLModel):
    messages: list[MessageOut]


class SendResponse(SQLModel):
    ok: bool

#classe qui defini un type session
class UserSession(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    user: User | None = Relationship(back_populates="sessions")
    token: str = Field(unique=True, index=True)

#classe pour recevoir les données de login et register depuis le navigateur
class LoginRequest(SQLModel):
    name: str
    password: str

#classe pour recevoir les données de register depuis le navigateur
class RegisterRequest(SQLModel):
    name: str
    password: str

#classe pour recevoir les données d'un message depuis le navigateur
class SendMessage(SQLModel):
    message: str

#hash le mdp
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

#cree un token de session aléatoire
def create_session_token() -> str:
    return secrets.token_hex(32)

#va chercher le token et relie alors la session à l'utilisateur 
def get_current_user(request: Request, session: Session) -> User | None:
    session_token = request.cookies.get("session_token")
    if session_token is None: #si y a pas de token dans les cookies return None
        return None
    statement = select(UserSession).where(UserSession.token == session_token)
    user_session = session.exec(statement).first() #recupere la session sinon
    if user_session is None: #si token pas valide : none
        return None
    statement = select(User).where(User.id == user_session.user_id) #recup le user mtn apartir session
    user = session.exec(statement).first()
    return user


@app.get("/chat", response_class=HTMLResponse) #crée une requete GET http avec chat, retoune page html
async def chat(request: Request):
    """Serve the chat client page. Returns HTTP 200 on success."""
    with Session(engine) as session: #ouvre une session avec les infos du user
        curr_user = get_current_user(request, session)
        if curr_user is None:
            return RedirectResponse(url="/login")
        
    return templates.TemplateResponse( #load la page chat1.html avec les infos du user
        request=request,
        name="chat_1.html",
        context={"user_name": curr_user.name},
    )


@app.get("/poll", response_model=PollResponse)
async def poll() -> PollResponse:
    """Return the current message history. Returns HTTP 200 on success."""
    with Session(engine) as session: 
        #va chercher les messages dans cette session 
        statement = select(ChatMessage).order_by(ChatMessage.id)
        messages = session.exec(statement).all()
        #on les mets en MessageOut pour les envoyer (messsage +user_name)
        messages_out = [MessageOut(message=msg.message, user_name=msg.user.name) for msg in messages]
        return PollResponse(messages=messages_out)


@app.get("/login") #acceder à la page de login
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login_0.html",
        context={},
    )

@app.post("/send", response_model=SendResponse) #envoie un message
async def send(request: Request, msg: SendMessage) -> SendResponse:
    """Store one new chat message. Returns HTTP 200 on success."""
    with Session(engine) as session:
        curr_user = get_current_user(request, session)
        if curr_user is None: # si user existe pas ou pas connecté : erreur 401
            raise HTTPException(status_code=401, detail="Unauthorized")
        #sinon crée un ChatMessage et le store dans la session
        chat_message = ChatMessage(message=msg.message, user_id=curr_user.id) 
        session.add(chat_message)
        session.commit()
    return SendResponse(ok=True)


@app.post("/register") #pour se créer un compte
async def register(data: RegisterRequest, response: Response):
    with Session(engine) as session:
        statement = select(User).where(User.name == data.name)
        usr = session.exec(statement).first()
        if usr is not None: #si existe deja on le dit : erreur
            raise HTTPException(status_code=400, detail="Utilisateur existe deja")
        else:
            #cree un nouveau user et le stocke (mdp hashé, crée user)
            new_user = User(name=data.name, password_hash=hash_password(data.password))
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            #crée une session pour ce user et stocke le token dans les cookies
            new_session = UserSession(token=create_session_token(), user_id=new_user.id)
            session.add(new_session)
            session.commit()

            response.set_cookie(key="session_token", value=new_session.token, httponly=True)

    return {"ok": True}


@app.post("/login") #pour se connecter à un compte déjà créé
async def login(data: LoginRequest, response: Response):
    with Session(engine) as session:    #va chercher le user avec ce nom et ce mdp hashé
        statement = select(User).where(User.name == data.name).where(User.password_hash == hash_password(data.password))
        usr = session.exec(statement).first()
        if usr is None: #si pas de user avec ce nom et ce mdp : erreur
            raise HTTPException(status_code=400, detail="Nom ou mot de passe incorrect")
        else:
            # si login ok cree une session et elle est stockée grace au token qui est relié à l'id de l'utilisateur, token gardé en stockage
            new_session = UserSession(token=create_session_token(), user_id=usr.id)
            session.add(new_session)
            session.commit()
            response.set_cookie(key="session_token", value=new_session.token, httponly=True)
    return {"ok": True}


@app.on_event("startup") #quand allume le truc cree base de données 
async def create_db_and_tables():
    return SQLModel.metadata.create_all(engine)