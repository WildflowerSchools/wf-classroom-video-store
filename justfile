set dotenv-load := true
version := "v0.16"

start-mongo:
    @docker-compose -f stack.yml run --rm -d mongo

format:
    black classroom_video

lint-app:
    @pylint classroom_video

start-app: lint-app
    @uvicorn classroom_video:app --reload --port 2300 --log-level=debug --log-config=log-config.yaml

build-docker: lint-app
    @docker-compose -f stack.yml --profile api --profile cli build

run-docker: build-docker
    @docker-compose -f stack.yml --profile api up -d

test:
    behave
