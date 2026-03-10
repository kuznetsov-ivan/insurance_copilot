from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from insurance_copilot.config import load_dotenv
load_dotenv(override=True)

from insurance_copilot.routes import api_router, web_router


def create_app() -> FastAPI:
    app = FastAPI(title="Insurance Co-Pilot", version="0.1.0")
    app.mount("/static", StaticFiles(directory="src/insurance_copilot/static"), name="static")
    app.include_router(web_router)
    app.include_router(api_router)
    return app


app = create_app()


def run() -> None:
    uvicorn.run("insurance_copilot.app:app", host="127.0.0.1", port=8000, reload=True)
