#!/bin/bash
curl -fsS http://localhost:8000/health || echo "API not ready"
docker compose ps
