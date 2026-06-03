from fastapi import FastAPI
from app.api import wecom_callback
from app.config import settings

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
