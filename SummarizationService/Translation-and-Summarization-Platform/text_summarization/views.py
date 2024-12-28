from django.contrib.sites import requests
from django.shortcuts import render
import requests
# Create your views here.
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.decorators import api_view
from django.http import HttpResponse
from .models import Text

from kafka import KafkaProducer, KafkaConsumer
import json
import threading
import os
import environ
env = environ.Env()
environ.Env.read_env()


KAFKA_SERVERS = 'localhost:9092'
# KAFKA_SERVERS = os.getenv("KAFKA_SERVERS", "localhost:9092")
SUMMARIZATION_REQUESTS_TOPIC = 'summarization-requests'
SUMMARIZATION_RESPONSES_TOPIC = 'summarization-responses'


# producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def send_summarization_request(request_data):
    print(f"[Producer] Sending summarization request: {request_data}")
    producer.send(SUMMARIZATION_RESPONSES_TOPIC, request_data)
    producer.flush()


def create_consumer(topic):
    return KafkaConsumer(
        topic,
        bootstrap_servers=KAFKA_SERVERS,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )


# consumer
def consume_summarization_responses():
    consumer = create_consumer(SUMMARIZATION_REQUESTS_TOPIC)
    print("[Consumer] Listening to summarization responses...")
    for message in consumer:
        print(f"[Summarization Response] Received: {message.value}")


def start_consumer_threads():
    summarization_thread = threading.Thread(target=consume_summarization_responses, daemon=True)

    summarization_thread.start()


API_URL = env('API')
TOKEN = env('TOKEN')
headers = {
    "Authorization": TOKEN,
    "Content-Type": "application/json"
}


@api_view(['Post'])
def summarized_text(request):
    start_consumer_threads()

    user_id = request.data.get("user_id")
    request_id = request.data.get("request_id")
    print(f"user id is {user_id} and request id is {request_id}")
    text = request.data.get("text")
    summarization_type = request.data.get("type", "formal").lower()  # Default to "formal"

    if not text:
        return Response({"error": "Text is required."}, status=status.HTTP_400_BAD_REQUEST)

    if summarization_type not in ["formal", "informal", "technical"]:
        return Response(
            {"error": "Invalid type. Choose from 'formal', 'informal', or 'technical'."},
            status=status.HTTP_400_BAD_REQUEST
        )

    text_status = Text.objects.create(status='pending')

    try:
        # Send the text to the external API
        print(requests.post(API_URL, json={"inputs": text}, headers=headers))
        api_response = requests.post(API_URL, json={"inputs": text}, headers=headers)
        print(f"api response is {api_response.json()}")
        # Check for successful response
        summary = api_response.json()

        print(type(api_response.json()))
        summary = api_response.json()[0]['summary_text']
        if api_response.status_code == 200:
            metadata = {"user_id": user_id, "request_id": request_id}
            text_status.status = 'processed'
            text_status.save()
            data = {
                **metadata,
                "text_id": text_status.pk,
                "type": summarization_type,
                "summary": summary
            }
            # send kafka
            send_summarization_request(data)
            return Response(data, status=status.HTTP_200_OK)

        else:
            return Response({
                "error": "Summarization failed.",
                "details": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        text_status.status = 'failed'
        text_status.save()
        return Response({
            "error": "Summarization failed.",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_status(request, text_id):
    try:
        # Retrieve the text instance by its ID
        text_instance = Text.objects.get(pk=text_id)

        # Convert the model instance to a dictionary and return it in the response
        text_data = {
            "id": text_instance.id,
            "status": text_instance.status,
            "timestamp": text_instance.timestamp,
        }

        return Response(text_data, status=status.HTTP_200_OK)

    except Text.DoesNotExist:
        return Response({"error": "Text not found"}, status=status.HTTP_404_NOT_FOUND)


def home(request):
    return HttpResponse("Hello, server!")


