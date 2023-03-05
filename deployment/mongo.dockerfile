FROM mongo:5

COPY custom-user.sh /docker-entrypoint-initdb.d/
