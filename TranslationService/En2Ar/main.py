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

# FastAPI app instance
app = FastAPI()

# Database setup
DATABASE_URL = f"sqlite:///./test.db"
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
API_URL = "https://api-inference.huggingface.co/models/Helsinki-NLP/opus-mt-en-ar"
headers = {
    "Authorization": "Bearer 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",
    "Content-Type": "application/json",
}

# Translate endpoint
@app.post("/translate")
async def translate(request: Request, db: Session = Depends(get_db)):
    # Parse request JSON
    request_data = await request.json()
    user_id = request_data.get("user_id")
    request_id = request_data.get("request_id")
    text = request_data.get("text")

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    # Create a task entry with 'pending' status
    text_status = Text(status="pending")
    db.add(text_status)
    try:
        db.commit()  # Ensure commit occurs here
        db.refresh(text_status)  # Refresh to get the ID after commit
    except Exception as e:
        db.rollback()  # Rollback in case of failure
        raise HTTPException(status_code=500, detail="Database commit failed")

    try:
        # Send the text to the external API
        api_response = requests.post(API_URL, json={"inputs": text}, headers=headers)

        if api_response.status_code == 200:
            translation = api_response.json()[0]['translation_text']
            metadata = {"user_id": user_id, "request_id": request_id}

            # Update task status to 'processed'
            text_status.status = "processed"
            db.commit()

            return JSONResponse({
                **metadata,
                "source_language": "en",
                "target_language": "ar",
                "translation": translation,
            })
        else:
            # Handle API errors
            raise HTTPException(status_code=500, detail="Translation failed.")

    except Exception as e:
        # Update task status to 'failed'
        text_status.status = "failed"
        db.commit()

        # Return error response
        raise HTTPException(status_code=500, detail=str(e))

# Status endpoint
@app.get("/status/{text_id}", response_model=TextResponse)
async def get_status(text_id: int, db: Session = Depends(get_db)):
    try:
        # Retrieve the task instance by its ID
        text_instance = db.query(Text).filter(Text.id == text_id).first()

        if not text_instance:
            raise HTTPException(status_code=404, detail="Task not found")

        # Return the Pydantic model (automatically serializes datetime)
        return text_instance  # FastAPI will automatically convert the SQLAlchemy model to TextResponse

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
