FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 CREWAI_DISABLE_TELEMETRY=true OTEL_SDK_DISABLED=true
WORKDIR /srv/trippy
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app ./app
CMD ["python","-m","app.host"]
