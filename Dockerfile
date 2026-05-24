FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml ./
COPY data_layer ./data_layer

RUN pip install --no-cache-dir fastapi uvicorn smartapi-python pyotp python-dotenv logzero pycryptodome websocket-client

EXPOSE 8000

CMD ["python", "-m", "data_layer.data_modes.rest.run_fastapi"]
