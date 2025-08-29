#!/bin/bash

CONF_FILE="server/config.ini"
BACKUP_FILE="config.ini.bak"
PORT="12345"

if [ ! -f "$CONF_FILE" ]; then
    echo "Error: no se encontró $CONF_FILE"
    exit 1
fi

cp "$CONF_FILE" "$BACKUP_FILE"
echo -e "[DEFAULT]\nSERVER_PORT = $PORT\nSERVER_IP = server\nSERVER_LISTEN_BACKLOG = 5\nLOGGING_LEVEL = INFO" > "$CONF_FILE"

MSG="test message"

sudo docker compose -f docker-compose-dev.yaml up server -d
OUTPUT=$(echo "$MSG" | sudo docker run -i --rm --network=tp0_testing_net busybox nc server "$PORT")

if [ "$OUTPUT" = "$MSG" ]; then
    echo "action: test_echo_server | result: success"
else
    echo "action: test_echo_server | result: fail"
fi

sudo docker compose -f docker-compose-dev.yaml down
mv -f "$BACKUP_FILE" "$CONF_FILE"

