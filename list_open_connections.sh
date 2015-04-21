#!/bin/bash
##
# Run this script on the machine running mosquitto to list all open client
# connections to the broker.
##

MQTT_PORT=1883

netstat -an | awk '{print $5}' | grep ":$MQTT_PORT"
