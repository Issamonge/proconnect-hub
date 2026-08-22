#!/bin/bash
docker compose up -d --build
bash scripts/healthcheck.sh
