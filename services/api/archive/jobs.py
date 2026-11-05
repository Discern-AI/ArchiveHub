"""Background jobs. "sync" runs inline (tests), "thread" uses a worker thread (local
development without Redis), "rq" uses Redis + RQ (production)."""

import threading

from django.conf import settings
from django.db import transaction


def enqueue(job_id) -> None:
    backend = settings.JOBS_BACKEND
    from .processing import run_job

    if backend == "sync":
        run_job(job_id)
    elif backend == "rq":
        import django_rq

        transaction.on_commit(lambda: django_rq.enqueue(run_job, job_id))
    else:
        transaction.on_commit(
            lambda: threading.Thread(target=run_job, args=(job_id,), daemon=True).start()
        )
