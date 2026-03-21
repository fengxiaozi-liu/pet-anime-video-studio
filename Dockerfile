FROM python:3.10-slim AS builder

WORKDIR /tmp/build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.10-slim AS runtime

WORKDIR /app/backend

RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

COPY --chown=appuser:appgroup backend /app/backend
COPY --chown=appuser:appgroup front /app/front
COPY --chown=appuser:appgroup config.yaml /app/config.yaml

RUN mkdir -p /app/uploads /app/outputs /app/data && \
    chown -R appuser:appgroup /app/uploads /app/outputs /app/data /app/backend /app/front

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000
ENV DEBUG=false

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
