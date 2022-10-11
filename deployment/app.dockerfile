FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

WORKDIR /app


COPY poetry.lock /app/
COPY pyproject.toml /app/pyproject.toml
COPY log-config.yaml /app/log-config.yaml
COPY classroom_video/ /app/classroom_video/

RUN pip install pipx && pipx install poetry
RUN /root/.local/bin/poetry config virtualenvs.create false && /root/.local/bin/poetry install --without dev --no-interaction --no-ansi


CMD ["uvicorn", "classroom_video:app", "--host", "0.0.0.0", "--port", "2300"]
