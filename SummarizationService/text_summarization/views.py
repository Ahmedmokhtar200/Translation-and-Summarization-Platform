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

API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
headers = {
    "Authorization":
        "Bearer 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",
        "Content-Type": "application/json"
}
# # Input text
# text = """
# Artificial intelligence (AI) refers to the simulation of human intelligence in machines
# that are programmed to think and learn. These machines can perform tasks that typically
# require human intelligence, such as visual perception, speech recognition, decision-making,
# and language translation. The field of AI has seen significant advancements in recent years,
# with applications ranging from self-driving cars to advanced robotics and predictive analytics.
# """

# from transformers import
# after testing change this to @api_view(['Post'])


@api_view(['Post'])
def summarized_text(request):

    # print(f"post request is {request.data.get("metadata")}")
    # metadata = request.data.get("metadata")

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
            return Response({
                **metadata,
                "type": summarization_type,
                "summary": summary
            }, status=status.HTTP_200_OK)

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

