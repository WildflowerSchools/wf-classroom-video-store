FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

WORKDIR /app


COPY poetry.lock /app/
COPY pyproject.toml /app/pyproject.toml
COPY log-config.yaml /app/log-config.yaml
COPY classroom_video/ /app/classroom_video/
COPY README.md /app/README.md

RUN pip install pipx && pipx install poetry

ENV PATH="/root/.local/bin:/root/.local/pipx/venvs/poetry/bin:${PATH}"


RUN poetry config virtualenvs.create false && /root/.local/bin/poetry install --without dev --no-interaction --no-ansi


CMD ["uvicorn", "classroom_video:app", "--host", "0.0.0.0", "--port", "2300"]
