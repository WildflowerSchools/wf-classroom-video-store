# Classroom Video Store

API to store indexed video from classrooms.

### Development

1) Copy `.env.template` to `.env` and, at a minimum, set `AUTH0_CLIENT_SECRET`
2) Deploy with docker-compose. This starts a Mongo database exposed on local port 27017 and a FastAPI service exposed on port 8082
```
just app-run-docker
```

#### Run CLI within Docker

A CLI is included. A separate Docker file exists `depoyment/cli.dockerfile` to prepare the CLI container. The container executes `scripts/run-cli.sh`.

**Example: Dry run with retention delta set to 1000 days and two environment ids provided**
```
docker compose -f ./stack.yml run --env DRY=true --env RETENTION_DELTA=1000 --env ENVIRONMENT_IDS="a,2831e832-d21b-4f29-8eb3-605618a176bd" cli
```

