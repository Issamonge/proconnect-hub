#!/bin/bash
# usage: bash scripts/restore_db.sh backups/proconnect-YYYYMMDD-HHMM.sql.gz
FILE=$1
gunzip -c $FILE | docker compose exec -T postgres psql -U proconnect proconnect
