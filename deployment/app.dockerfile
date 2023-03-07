FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

WORKDIR /app

RUN apt update -y && pip install pipx && pipx install poetry

COPY poetry.lock pyproject.toml /app/

ENV PATH="/root/.local/bin:/root/.local/pipx/venvs/poetry/bin:${PATH}"
RUN poetry config virtualenvs.create false && poetry install --without dev --no-interaction --no-ansi  --no-root

COPY log-config.yaml /app/log-config.yaml
COPY classroom_video/ /app/classroom_video/

CMD ["uvicorn", "classroom_video:app", "--host", "0.0.0.0", "--port", "2300"]
