#!/bin/bash

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start the app
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT