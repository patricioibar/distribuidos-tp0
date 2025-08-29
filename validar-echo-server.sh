#!/bin/bash

CONF_FILE="server/config.ini"
PORT="12345"

if [ ! -f "$CONF_FILE" ]; then
    echo "Error: no se encontró $CONF_FILE"
    exit 1
fi

source "$CONF_FILE"

if [ -z "$PORT" ]; then
  echo "Error: el archivo $CONF_FILE debe definir PORT"
  exit 1
fi


MSG="test message"

OUTPUT=$(echo "$MSG" | sudo docker run -i --rm --network=tp0_testing_net busybox nc server "$PORT")

if [ "$OUTPUT" = "$MSG" ]; then
    echo "action: test_echo_server | result: success"
else
    echo "action: test_echo_server | result: fail"
fi