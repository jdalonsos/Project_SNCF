FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Copy the project (Dockerfile lives inside Project_SNCF)
COPY . /app

RUN chmod +x /app/Scripts/*.sh || true

#
# Create docker_install.sh (POSIX version of your Scripts/install.sh)
#
RUN /bin/sh -c "printf '%s\n' \
    '#!/usr/bin/env bash' \
    'set -e' \
    'cd /app' \
    'python3 -m venv .venv' \
    'source .venv/bin/activate' \
    'pip install --upgrade pip' \
    'pip install poetry' \
    'poetry config virtualenvs.create false --local || true' \
    'poetry install --no-interaction --no-ansi --no-root' \
    > /app/Scripts/docker_install.sh"

RUN chmod +x /app/Scripts/docker_install.sh

# Run dependency install at build time
RUN /app/Scripts/docker_install.sh


#
# Create docker_launch.sh (POSIX version of launch.sh)
#
RUN /bin/sh -c "printf '%s\n' \
    '#!/usr/bin/env bash' \
    'set -euo pipefail' \
    '' \
    'printf \"\\n==============================================\\n\"' \
    'printf \"Streamlit app (open in your browser):\\n\"' \
    'printf \"  • http://localhost:8501\\n\"' \
    'printf \"  • http://host.docker.internal:8501  (if supported)\\n\\n\"' \
    'printf \"==============================================\\n\\n\"' \
    '' \
    'cd /app' \
    'source .venv/bin/activate' \
    'exec poetry run streamlit run app/main.py --server.address 0.0.0.0 --server.port 8501' \
    > /app/Scripts/docker_launch.sh"

RUN chmod +x /app/Scripts/docker_launch.sh

EXPOSE 8501

CMD ["/bin/bash", "Scripts/docker_launch.sh"]
