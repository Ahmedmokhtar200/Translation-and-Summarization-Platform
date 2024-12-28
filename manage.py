#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

from kafka import KafkaProducer, KafkaConsumer
import json
import threading
import os

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


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SummrizationService.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    start_consumer_threads()
    main()
