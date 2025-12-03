FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends\
    gcc build-essential curl jq && \
    rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app

# 🔧 Fix Windows CRLF and make scripts executable
RUN sed -i 's/\r$//' /app/Scripts/*.sh && \
    chmod +x /app/Scripts/*.sh

# Install dependencies using your install.sh
RUN /app/Scripts/install.sh

# Collect data
RUN /app/Scripts/collect_api.sh

EXPOSE 8501

CMD ["/bin/bash", "Scripts/launch.sh"]
