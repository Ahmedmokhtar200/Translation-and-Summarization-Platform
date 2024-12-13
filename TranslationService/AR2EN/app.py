from flask import Flask, request, jsonify, abort
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session ,declarative_base
import requests
import os
from datetime import datetime

# Flask app instance
app = Flask(__name__)

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


# External API details
API_URL = "https://api-inference.huggingface.co/models/Helsinki-NLP/opus-mt-ar-en"
headers = {
    "Authorization": "Bearer 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",
    "Content-Type": "application/json",
}

tasks = {}


@app.route("/translate", methods=["POST"])
def translate():
    # Parse request JSON
    request_data = request.get_json()
    user_id = request_data.get("user_id")
    request_id = request_data.get("request_id")
    text = request_data.get("text")

    print(f"user id is {user_id} request id is {request_id} text is {text}")
    if not text:
        abort(400, description="Text is required")

    db = SessionLocal()
    # Create a task entry with 'pending' status
    text_status = Text(status="pending")
    db.add(text_status)
    try:
        db.commit()  # Ensure commit occurs here
        db.refresh(text_status)  # Refresh to get the ID after commit
        print(f"Text status added with ID {text_status.id} and status 'pending'")
    except Exception as e:
        db.rollback()  # Rollback in case of failure
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
            db.commit()

            db.close()
            return jsonify({
                **metadata,
                "source_language": "ar",
                "target_language": "en",
                "translation": translation,
            })
        else:
            # Handle API errors
            db.close()
            abort(500, description="Translation failed.")
    except Exception as e:
        # Update task status to 'failed'
        text_status.status = "failed"
        db.commit()

        db.close()
        # Return error response
        abort(500, description=str(e))


@app.route("/status/<int:task_id>", methods=["GET"])
def get_task_status(task_id):
    """
    Get the status of a translation task.
    :param task_id: The unique task ID.
    :return: The task status and result if completed.
    """
    db = SessionLocal()
    task = db.query(Text).filter(Text.id == task_id).first()

    if not task:
        db.close()
        abort(404, description="Task not found")

    # Return the task status and result
    db.close()
    return jsonify({
        "task_id": task.id,
        "status": task.status,
        "result": task.timestamp if task.status == "processed" else "In progress"
    })


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8003)
