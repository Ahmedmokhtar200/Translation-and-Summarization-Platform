from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
import requests
import os
from datetime import datetime
import uvicorn
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv('URL')
TOKEN = os.getenv('TOKEN')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
# FastAPI app instance
app = FastAPI()

# Database setup
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@en2ar-db:5432/{POSTGRES_DB}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class Text(Base):
    __tablename__ = "text"
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, index=True)
    timestamp = Column(DateTime, server_default=func.now(), index=True)

# Create tables
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Response Model
class TextResponse(BaseModel):
    id: int
    status: str
    timestamp: datetime  # datetime type will be automatically serialized to string

    class Config:
        # Tell Pydantic to treat the SQLAlchemy models as dicts
        from_attributes = True

# External API details
API_URL = os.getenv('URL')
headers = {
    "Authorization": os.getenv('TOKEN'),
    "Content-Type": "application/json",
}

# Translate endpoint
@app.post("/en2ar/translate")
async def translate(request: Request, db: Session = Depends(get_db)):
    request_data = await request.json()
    user_id = request_data.get("user_id")
    request_id = request_data.get("request_id")
    text = request_data.get("text")

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    text_status = Text(status="pending")
    db.add(text_status)
    try:
        db.commit()
        db.refresh(text_status)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database commit failed")

    try:
        api_response = requests.post(API_URL, json={"inputs": text}, headers=headers)
        if api_response.status_code == 200:
            translation = api_response.json()[0]['translation_text']
            metadata = {"user_id": user_id, "request_id": request_id}

            text_status.status = "processed"
            db.commit()

            return JSONResponse({
                **metadata,
                "text_id": text_status.id,
                "source_language": "en",
                "target_language": "ar",
                "translation": translation,
            })
        else:
            raise HTTPException(status_code=500, detail="Translation failed.")
    except Exception as e:
        text_status.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

# Status endpoint
@app.get("/en2ar/translate/status/{text_id}", response_model=TextResponse)
async def get_status(text_id: int, db: Session = Depends(get_db)):
    try:
        text_instance = db.query(Text).filter(Text.id == text_id).first()
        if not text_instance:
            raise HTTPException(status_code=404, detail="Task not found")
        return text_instance
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
