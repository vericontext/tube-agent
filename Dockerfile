FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY pyproject.toml .
COPY scripts/ scripts/
COPY tube_agent/ tube_agent/
RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "tube_agent.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
