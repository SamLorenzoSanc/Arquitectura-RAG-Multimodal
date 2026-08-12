FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn[standard] paho-mqtt asyncpg pydantic
COPY main.py .
ENV PYTHONUNBUFFERED=1
EXPOSE 50053
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "50053"]
