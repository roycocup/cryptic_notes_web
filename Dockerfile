FROM python:3.10.5-slim-bullseye

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY prod-requirements.txt ./
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r prod-requirements.txt

COPY . ./

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
