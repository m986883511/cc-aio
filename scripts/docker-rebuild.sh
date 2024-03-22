#!/usr/bin/env bash
docker inspect -f "$(cat /usr/local/astute/scripts/docker-run.tpl)" $1 | tee /run/$1.tpl
