#!/usr/bin/env bash
AUTHOR_NAME="cg"
docker inspect -f "$(cat /usr/local/$AUTHOR_NAME/scripts/docker-run.tpl)" $1 | tee /run/$1.tpl
