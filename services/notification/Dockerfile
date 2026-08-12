FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn[standard] paho-mqtt
COPY main.py .
ENV PYTHONUNBUFFERED=1
EXPOSE 50055
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "50055"]
