# 🍞 Bakery Management System (Dockerized)

## 🔧 Components

- PostgreSQL (Database)
- FastAPI (Backend)
- Nginx (Frontend)
- RabbitMQ (Message Queue)
- Optional: Redis, Logging, Health Checks

## 📦 Setup Instructions

```bash
git clone <repo>
cd <repo>
docker-compose up --build
```

Access:

- Frontend: http://localhost:8080 
- Backend: http://localhost:8000
- RabbitMQ: http://localhost:15672

## 📚 API Endpoints

| Method | Endpoint          | Description              |
| ------ | ----------------- | ------------------------ |
| GET    | /products         | List bakery items        |
| POST   | /order            | Place a new order        |
| GET    | /order/{order_id} | Check status of an order |

## 📘 Design Notes

- Docker Compose orchestrates all services.
- RabbitMQ decouples backend and order processor.
- Health checks ensure container reliability.
