"""Background jobs. "sync" runs inline (tests), "thread" uses a worker thread (local
development without Redis), "rq" uses Redis + RQ (production)."""

import threading

from django.conf import settings
from django.db import transaction


def enqueue(job_id) -> None:
    backend = settings.JOBS_BACKEND
    from .processing import run_job, run_job_in_worker

    if backend == "sync":
        # Same thread and connection as the request: no connection housekeeping.
        run_job(job_id)
    elif backend == "rq":
        import django_rq

        transaction.on_commit(lambda: django_rq.enqueue(run_job_in_worker, job_id))
    else:
        transaction.on_commit(
            lambda: threading.Thread(target=run_job_in_worker, args=(job_id,), daemon=True).start()
        )
