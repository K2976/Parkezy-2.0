#!/bin/sh
# Render free plan has no background workers, so the Celery worker (with embedded beat) runs next to
# the API in this one container. Without it the outbox is never drained: no emails, no push, no
# booking expiries. Measured ~340 MB with one web worker, inside the free 512 MB.
# ponytail: one container for both; on a paid plan run the worker as a Render Background Worker
# (same image, command `celery -A app.workers.celery_app worker -B`) and use the Dockerfile CMD here.
set -e
alembic upgrade head
# If Celery ever exits, stop the API too ($$ becomes uvicorn's pid after exec) so Render restarts the
# whole container instead of serving requests whose emails would silently never be sent.
(celery -A app.workers.celery_app worker -B --pool=solo --loglevel=INFO; echo "celery exited; restarting" >&2; kill -TERM $$) &
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WEB_CONCURRENCY:-1}" --proxy-headers --no-access-log
