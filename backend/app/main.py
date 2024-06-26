"""Main module for the FastAPI application.

This module initializes the FastAPI application, database, and includes all the routes.
It also sets up CORS (Cross-Origin Resource Sharing) to allow requests from specified origins.

Functions:
    create_db(): Initializes the database by creating all tables.

Imports:
    FastAPI: Class to create a new FastAPI instance.
    CORSMiddleware: Middleware for managing CORS.
    create_db: Function to initialize the database.
    router: FastAPI router containing all application routes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db.conn import create_db
from .router.user import router as userRouter
from .router.liveness import router as liveRouter

create_db()

app = FastAPI()
app.include_router(userRouter)
app.include_router(liveRouter)

# CORS configuration
origins = [
    "http://localhost:9080",  # Adjust this as needed
    "http://localhost:8080",  # Adjust this as needed
    "http://localhost:3000",  # Adjust this as needed
    "http://localhost:8000",  # Adjust this as needed
    "http://local.adrianlopes-swe.com.br",  # Adjust this as needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
