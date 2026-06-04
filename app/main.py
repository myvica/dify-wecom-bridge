from fastapi import FastAPI
import logging
from logging.handlers import RotatingFileHandler
from app.api import wecom_callback
from app.config import settings

log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

root_logger = logging.getLogger()
root_logger.setLevel(log_level)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
root_logger.addHandler(console_handler)

if settings.log_file:
    from pathlib import Path as _Path
    _Path(settings.log_file).parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        settings.log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)

app = FastAPI(title="Dify WeCom Bridge v2", version="2.0.0")

app.include_router(wecom_callback.router)


@app.get("/")
async def root():
    return {"message": "Dify WeCom Bridge v2 is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
