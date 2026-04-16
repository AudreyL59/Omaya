from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title=os.getenv('APP_NAME', 'ERP Omaya'),
    version=os.getenv('APP_VERSION', '1.0.0')
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://sos.adm.omaya.fr", "https://newadm.omaya.fr", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/')
def read_root():
    return {'status': 'ok', 'message': 'ERP Omaya API is running'}
