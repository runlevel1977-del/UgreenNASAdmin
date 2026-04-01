FROM python:3.12-slim

WORKDIR /app

COPY web/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY web/api/app /app/app
COPY nas_ssh.py /app/nas_ssh.py
COPY nas_utils.py /app/nas_utils.py

ENV PYTHONUNBUFFERED=1
ENV APP_DATA_DIR=/app_data

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
