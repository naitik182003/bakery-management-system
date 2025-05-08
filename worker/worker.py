import pika
import json
import time
import requests
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("worker")

def callback(ch, method, properties, body):
    try:
        # Parse the order data
        order_data = json.loads(body)
        order_id = order_data["order_id"]
        
        logger.info(f"Processing order: {order_data}")
        
        # Simulate processing time
        logger.info(f"Baking goods for order {order_id}...")
        time.sleep(5)  # Simulate work being done
        
        # Update order status to "processing"
        response = requests.put(
            f"http://backend:8000/order/{order_id}",
            json={"status": "processing"}
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to update order status to processing: {response.text}")
        
        # More processing
        logger.info(f"Packaging order {order_id}...")
        time.sleep(3)  # More simulated work
        
        # Update order status to "completed"
        response = requests.put(
            f"http://backend:8000/order/{order_id}",
            json={"status": "completed"}
        )
        
        if response.status_code == 200:
            logger.info(f"Order {order_id} has been completed successfully!")
        else:
            logger.error(f"Failed to update order status: {response.text}")
            
    except Exception as e:
        logger.error(f"Error processing order: {e}")

def main():
    # Connection retry logic
    max_retries = 30
    retries = 0
    
    while retries < max_retries:
        try:
            logger.info(f"Attempt {retries+1} to connect to RabbitMQ...")
            connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
            channel = connection.channel()
            channel.queue_declare(queue='orders')
            
            logger.info("Worker started successfully. Waiting for messages...")
            
            channel.basic_consume(
                queue='orders',
                on_message_callback=callback,
                auto_ack=True
            )
            
            channel.start_consuming()
            break
            
        except pika.exceptions.AMQPConnectionError:
            retries += 1
            logger.warning(f"Failed to connect to RabbitMQ. Retrying in 5 seconds...")
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            sys.exit(1)
    
    if retries >= max_retries:
        logger.error("Maximum connection attempts reached. Exiting.")
        sys.exit(1)

if __name__ == "__main__":
    main()