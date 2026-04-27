# Follow to install

```
git clone https://github.com/eleonoredt/chat_abada_douet
cd chat_abada_douet
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install "fastapi[standard]" sqlmodel
```

# Run Backend
```
fastapi dev chat_server_3.py
```

# Open Web App
- [http://127.0.0.1:8000/login](http://127.0.0.1:8000/login)
- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)