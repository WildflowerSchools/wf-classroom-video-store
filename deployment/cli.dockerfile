FROM python:3.9-slim

WORKDIR /app

RUN apt update -y && pip install --upgrade pip poetry wheel

COPY poetry.lock pyproject.toml /app/

RUN poetry config virtualenvs.create false && poetry install --without dev --no-interaction --no-ansi  --no-root

COPY log-config.yaml /app/log-config.yaml
COPY classroom_video/ /app/classroom_video/
COPY scripts/ /app

CMD bash /app/run-cli.sh