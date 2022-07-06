FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

WORKDIR /app


COPY requirements.txt /app/requirements.txt
COPY log-config.yaml /app/log-config.yaml

RUN pip install -r /app/requirements.txt


COPY classroom_video/ /app/classroom_video/

CMD ["uvicorn", "classroom_video:app", "--host", "0.0.0.0", "--port", "2300"]
