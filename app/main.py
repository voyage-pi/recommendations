from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import trip

app = FastAPI()


app.include_router(trip.router)

origins = [
    "http://localhost:8080",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
