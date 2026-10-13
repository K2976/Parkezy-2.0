# Parkezy

Two-sided parking marketplace for drivers and hosts.

## Repository Structure

This repository is organized into the following modules:

- **[`parkezy-innotech/`](./parkezy-innotech)**: The production full-stack Parkezy application:
  - **`mobile/`**: Cross-platform Expo (React Native) mobile app for iOS and Android (map search, QR check-in/out, booking flows, and host management).
  - **`backend/`**: FastAPI API server, PostgreSQL + PostGIS, Redis caching & bloom filters, Celery asynchronous workers.
  - **`docker-compose.yml`**: Local development infrastructure (PostgreSQL, Redis, SeaweedFS S3, Mailpit).
  - **`docs/`**: Architecture Decision Records (ADRs) and product requirements.
  - **`system-design-notes/`**: Distributed systems and architecture notes.

- **[`parkezy-2.0/`](./parkezy-2.0)**: Legacy project archive, native iOS Xcode project, and audit documentation.

## Quick Start (Parkezy Innotech)

For full documentation and environment setup, see [`parkezy-innotech/README.md`](./parkezy-innotech/README.md).

```bash
# 1. Start Infrastructure
cd parkezy-innotech
docker compose up -d

# 2. Run Backend
cd backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# 3. Run Mobile App
cd ../mobile
cp .env.example .env
npm install
npx expo start
```
