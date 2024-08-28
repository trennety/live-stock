import pika
import pymongo
import json
import os

# Konfigurationen aus Umgebungsvariablen laden
rabbitmq_host = os.getenv('RABBITMQ_HOST', 'rabbitmq')
rabbitmq_port = int(os.getenv('RABBITMQ_PORT', 5672))
queue_name = os.getenv('QUEUE_NAME', 'default_queue')
mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://mongo1:27017,mongo2:27018,mongo3:27019/?replicaSet=rs0')
mongodb_db = 'stockmarket'
mongodb_collection = 'stocks'

# Verbindung zu RabbitMQ herstellen
try:
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host, port=rabbitmq_port))
    channel = connection.channel()
    print(f"Connecting to RabbitMQ at {rabbitmq_host}:{rabbitmq_port}")
except pika.exceptions.AMQPConnectionError as e:
    print(f"Failed to connect to RabbitMQ at {rabbitmq_host}:{rabbitmq_port} - {str(e)}")
    exit(1)

# Verbindung zu MongoDB herstellen
try:
    client = pymongo.MongoClient(mongodb_uri)
    db = client[mongodb_db]
    collection = db[mongodb_collection]
    print(f"Connecting to MongoDB at {mongodb_uri}")
except pymongo.errors.ServerSelectionTimeoutError as e:
    print(f"Failed to connect to MongoDB at {mongodb_uri} - {str(e)}")
    exit(1)

# Zähler und Summen für die Berechnung des Durchschnittspreises
message_count = 0
total_price = 0.0

def callback(ch, method, properties, body):
    global message_count, total_price
    
    data = json.loads(body)
    price = float(data['price'])
    
    # Nachrichten zählen und Gesamtpreis summieren
    message_count += 1
    total_price += price

    # Durchschnitt berechnen und ausgeben, wenn 1000 Nachrichten verarbeitet wurden
    if message_count == 1000:
        avg_price = round(total_price / message_count, 2)
        print(f"Durchschnittspreis nach 1000 Nachrichten: {avg_price}")

        # Durchschnittspreis in die MongoDB speichern
        collection.update_one(
            {'type': 'average_price'},
            {'$set': {'avgPrice': avg_price}},
            upsert=True
        )
        
        # Zähler und Summe zurücksetzen
        message_count = 0
        total_price = 0.0

    ch.basic_ack(delivery_tag=method.delivery_tag)

# RabbitMQ Queue konsumieren
channel.basic_consume(queue=queue_name, on_message_callback=callback)

print(f" [*] Waiting for messages in {queue_name}. To exit press CTRL+C")
channel.start_consuming()
