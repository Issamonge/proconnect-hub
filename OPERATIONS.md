# Operations

## Services
postgres, redis, api, worker, scheduler, dashboard, nginx.

## Common commands
```bash
docker compose ps
docker compose logs -f api
bash scripts/backup_db.sh
bash scripts/restore_db.sh backups/xxxx.sql.gz
```

## Data
PostgreSQL is the source of truth. data/*.json are legacy/import-only.

## Schedules (scheduler container)
- discover_buyers every 12h
- discover_businesses daily
- match every 6h
- backup daily
- cleanup (archive >7-day intent signals) daily
