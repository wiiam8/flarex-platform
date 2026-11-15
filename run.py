"""Start FLARE-X:  python run.py   then open http://127.0.0.1:8000   (HOST and PORT env vars are honoured)"""
import os
import uvicorn

if __name__ == "__main__":
    uvicorn.run("backend.api:app", host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
