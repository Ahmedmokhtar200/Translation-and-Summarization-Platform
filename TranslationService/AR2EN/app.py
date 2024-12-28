from flask import Flask, request, jsonify, abort
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv('URL')
TOKEN = os.getenv('TOKEN')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
# Flask app instance
app = Flask(__name__)

# PostgreSQL
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@ar2en-db:5432/{POSTGRES_DB}"  
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

# External API details
API_URL = API_URL
headers = {
    "Authorization": TOKEN,
    "Content-Type": "application/json",
}

tasks = {}

@app.route("/ar2en/translate", methods=["POST"])
def translate():
    # Parse request JSON
    request_data = request.get_json()
    user_id = request_data.get("user_id")
    request_id = request_data.get("request_id")
    text = request_data.get("text")

    if not text:
        abort(400, description="Text is required")

    db = SessionLocal()
    # Create a task entry with 'pending' status
    text_status = Text(status="pending")
    db.add(text_status)
    try:
        db.commit()
        db.refresh(text_status)
    except Exception as e:
        db.rollback()
        db.close()
        abort(500, description="Database commit failed")

    try:
        # Send the text to the external API
        api_response = requests.post(API_URL, json={"inputs": text}, headers=headers)

        if api_response.status_code == 200:
            translation = api_response.json()[0]['translation_text']
            metadata = {"user_id": user_id, "request_id": request_id}

            # Update task status to 'processed'
            text_status.status = "processed"
            text_id = text_status.id
            db.commit()

            db.close()
            return jsonify({
                **metadata,
                "text_id": text_id,
                "source_language": "ar",
                "target_language": "en",
                "translation": translation,
            })
        else:
            db.close()
            abort(500, description="Translation failed.")
    except Exception as e:
        text_status.status = "failed"
        db.commit()
        db.close()
        abort(500, description=str(e))

@app.route("/ar2en/translate/status/<int:task_id>", methods=["GET"])
def get_task_status(task_id):
    db = SessionLocal()
    task = db.query(Text).filter(Text.id == task_id).first()

    if not task:
        db.close()
        abort(404, description="Task not found")

    db.close()
    return jsonify({
        "task_id": task.id,
        "status": task.status,
        "result": task.timestamp if task.status == "processed" else "In progress"
    })

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8003)

