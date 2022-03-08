set dotenv-load := true
version := "v0.12"



docker-network:
    @docker network create classroom-events


start-mongo:
    @docker run -p 27017:27017 --network classroom-events \
        -v classroom-events-db:/data/db \
         optimuspaul/underground-cavern:mongodb5-v1


lint-app:
    @pylint classroom_video

start-app: lint-app
    @uvicorn classroom_video:app --reload --port 2300 --log-level=debug --log-config=log-config.yaml

app-build-docker: lint-app
    @docker build -t wildflowerschools/wf-classroom-video-store:{{version}} -f deployment/app.dockerfile .
    @docker push wildflowerschools/wf-classroom-video-store:{{version}}

app-run-docker: app-build-docker
    @docker run -p 2300:80 --network classroom-events \
        -e "WF_MONGODB_HOST=ce_mongo" \
        -e "WF_MONGODB_USER=wildflower" \
        -e "WF_MONGODB_PASS=unreal" \
        -e "WF_DATA_PATH=./data" \
        wildflowerschools/wf-classroom-video-store:{{version}}
