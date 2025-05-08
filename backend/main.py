from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import pika
import json
import logging
import os
import redis
import time
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from logging.config import dictConfig

# Logging setup
logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "INFO",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "app": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
dictConfig(logging_config)
logger = logging.getLogger("app")

# DB Setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db/bakery")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis Setup
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
redis_client = redis.Redis.from_url(REDIS_URL)
CACHE_EXPIRATION = 300  # 5 minutes

# Models
class ProductModel(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    price = Column(Float)
    stock = Column(Integer)

class OrderModel(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True, index=True)
    product_id = Column(Integer)
    quantity = Column(Integer)
    status = Column(String, default="pending")

# Create DB Tables
Base.metadata.create_all(bind=engine)

# App Init
app = FastAPI()

# CORS
origins = [
    "http://localhost:8080",
    "http://localhost",
    "http://frontend",
    "*",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Schemas
class Order(BaseModel):
    product_id: int
    quantity: int

class OrderStatus(BaseModel):
    status: str

# Health Check
@app.get("/health")
def health_check():
    return {"status": "ok"}

# Init sample products if empty
def init_db():
    db = SessionLocal()
    if db.query(ProductModel).count() == 0:
        logger.info("Seeding sample products")
        db.add_all([
            ProductModel(id=1, name="Bread", price=20, stock=100),
            ProductModel(id=2, name="Cake", price=100, stock=50),
            ProductModel(id=3, name="Croissant", price=30, stock=75),
            ProductModel(id=4, name="Donut", price=15, stock=120),
        ])
        db.commit()
    db.close()

@app.on_event("startup")
async def startup_event():
    logger.info("App starting...")
    for _ in range(5):
        try:
            redis_client.ping()
            logger.info("Redis connected")
            break
        except redis.exceptions.ConnectionError:
            logger.warning("Waiting for Redis...")
            time.sleep(2)
    init_db()

# List Products
@app.get("/products")
def list_products(db: Session = Depends(get_db)):
    cached = redis_client.get("all_products")
    if cached:
        logger.info("Returning cached products")
        return json.loads(cached)

    logger.info("Querying DB for products")
    products = db.query(ProductModel).all()
    result = [{"id": p.id, "name": p.name, "price": p.price, "stock": p.stock} for p in products]
    redis_client.setex("all_products", CACHE_EXPIRATION, json.dumps(result))
    return result

# Place Order
@app.post("/order")
def place_order(order: Order, db: Session = Depends(get_db)):
    logger.info(f"Placing order: Product {order.product_id}, Quantity {order.quantity}")
    product = db.query(ProductModel).filter(ProductModel.id == order.product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.stock < order.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")

    order_id = str(uuid.uuid4())
    db_order = OrderModel(id=order_id, product_id=order.product_id, quantity=order.quantity)
    db.add(db_order)
    product.stock -= order.quantity
    db.commit()
    redis_client.delete("all_products")

    order_data = {
        "order_id": order_id,
        "product_id": order.product_id,
        "quantity": order.quantity
    }

    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
        channel = connection.channel()
        channel.queue_declare(queue='orders')
        channel.basic_publish(exchange='', routing_key='orders', body=json.dumps(order_data))
        connection.close()
        logger.info(f"Order {order_id} sent to RabbitMQ")
    except Exception as e:
        logger.error(f"Failed to send order to RabbitMQ: {e}")

    return {"order_id": order_id, "status": "pending"}

# Get Order Status
@app.get("/order/{order_id}")
def check_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "order_id": order.id,
        "product_id": order.product_id,
        "quantity": order.quantity,
        "status": order.status
    }
