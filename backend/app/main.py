"""Main module for the FastAPI application.

This module initializes the FastAPI application, database, and includes all the routes.
It also sets up CORS (Cross-Origin Resource Sharing) to allow requests from specified origins.

Functions:
    create_db(): Initializes the database by creating all tables.

Imports:
    FastAPI: Class to create a new FastAPI instance.
    CORSMiddleware: Middleware for managing CORS.
    create_db: Function to initialize the database.
    router: FastAPI router containing all application routes. """

import asyncio

from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from app.messages.event import UpdateEvent
from app.messages.subscriber import AsyncListener

from .db.conn import create_db
from .db.settings import ENV
from .router.enterprise import router as enterpriseRouter
from .router.liveness import router as liveRouter
from .router.login import router as loginRouter
from .router.user import router as userRouter


create_db()


external_update_listener = AsyncListener(
    "external.rh_event", UpdateEvent.process_message
)


@asynccontextmanager
async def listener_span(fapi_app: FastAPI, *args, **kwargs):
    # pylint: disable=unused-argument

    loop = asyncio.get_running_loop()
    task = loop.create_task(external_update_listener.listen(loop))
    yield
    await task


app = FastAPI()
app.include_router(userRouter)
app.include_router(liveRouter)
app.include_router(enterpriseRouter)
app.include_router(loginRouter)

app.router.lifespan_context = listener_span

# CORS configuration
origins = [
    "http://local.adrianlopes-swe.com.br",
    "http://app.adrianlopes-swe.com.br",
    "https://apirh.adrianlopes-swe.com.br",
    "https://apisell.adrianlopes-swe.com.br",
    "https://apipt.adrianlopes-swe.com.br",
    "https://apirh.adrianlopes-swe.com.br:32747",
    "https://apisell.adrianlopes-swe.com.br:32747",
    "https://apipt.adrianlopes-swe.com.br:32747",
    "https://openferp.budibase.app"
]

if ENV == "test":
    origins = [
        *origins,
        "http://localhost:9080",
        "http://localhost:8080",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
