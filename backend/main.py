"""
TruthGuard AI — FastAPI Application Entry Point
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router

app = FastAPI(
    title="TruthGuard AI",
    description="Agentic AI Research & Fact-Checking System",
    version="1.0.0",
)

# CORS — allow all origins so the frontend can call directly (no proxy needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch any unhandled exception and return a clean JSON response.
    Manually adds CORS headers so the browser doesn't see 'Failed to fetch'.
    """
    err_msg = str(exc)
    print(f"[GlobalError] {type(exc).__name__}: {err_msg[:200]}")

    # Make common errors human-readable
    if "rate_limit_exceeded" in err_msg or "429" in err_msg:
        err_msg = (
            "Groq API daily token limit reached (100k tokens/day on free tier). "
            "Please wait a few minutes and try again, or switch to a smaller model "
            "(e.g. llama3-8b-8192) in backend/app/core/config.py."
        )
    elif "APIConnectionError" in type(exc).__name__ or "Connection error" in err_msg:
        err_msg = (
            "Cannot connect to Groq API. Please check your internet connection "
            "and verify your GROQ_API_KEY in the .env file."
        )

    return JSONResponse(
        status_code=500,
        content={"detail": err_msg},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "TruthGuard AI is running. Visit /docs for API documentation."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
