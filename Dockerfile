FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core snmp \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY daily_brief/ ./daily_brief/

ENTRYPOINT ["python", "-m", "daily_brief"]
CMD ["--print"]
