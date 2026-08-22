#!/bin/bash
mkdir -p backups
docker compose exec -T postgres pg_dump -U proconnect proconnect | gzip > backups/proconnect-$(date +%Y%m%d-%H%M).sql.gz
ls -lh backups/ | tail -5
