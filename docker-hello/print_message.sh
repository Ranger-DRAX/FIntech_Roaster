#!/bin/bash
MESSAGES=("Docker is fun!" "Containers rock!" "You're a Docker pro now!")
RANDOM_MESSAGE=${MESSAGES[$RANDOM % ${#MESSAGES[@]}]}
figlet -f slant "$RANDOM_MESSAGE"