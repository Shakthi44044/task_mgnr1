#!/bin/sh
set -e

if [ -n "$DATABASE_URL" ]; then
  echo "[entrypoint] Waiting for database... $DATABASE_URL"
  python <<'PYCODE'
import os, time, sys
from sqlalchemy import create_engine, text
url=os.environ.get('DATABASE_URL')
for i in range(30):
    try:
        engine=create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        print('[entrypoint] Database ready')
        break
    except Exception as e:
        print(f'[entrypoint] DB not ready ({i+1}/30): {e}')
        time.sleep(2)
else:
    print('[entrypoint] Database not reachable, exiting', file=sys.stderr)
    sys.exit(1)
PYCODE
fi

exec "$@"
