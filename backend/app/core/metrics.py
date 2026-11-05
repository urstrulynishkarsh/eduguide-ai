"""Numbers for monitoring, in the Prometheus format (docs/01 §1.9).

The API and the worker each serve them on METRICS_PORT, a port of its own that is never published
(infra/monitoring/prometheus.yml collects them). Labels are names and outcomes only: never ids,
people's names or any text from a family.
"""

import threading

from prometheus_client import Counter, Histogram, start_http_server

HTTP_REQUESTS = Counter(
    "eduguide_http_requests_total", "Requests answered by the API.", ["method", "route", "status"]
)
HTTP_SECONDS = Histogram(
    "eduguide_http_request_duration_seconds", "Time the API took to answer.", ["method", "route"]
)
JOBS = Counter("eduguide_jobs_total", "Background jobs run, by how they ended.", ["job", "outcome"])
JOB_SECONDS = Histogram(
    "eduguide_job_duration_seconds",
    "Time a background job ran.",
    ["job"],
    buckets=(1, 5, 15, 60, 300, 900, 1800, 3600, 7200),
)
AI_REQUESTS = Counter(
    "eduguide_ai_requests_total",
    "Calls to the AI provider, by how they ended.",
    ["provider", "tier", "outcome"],
)
AI_TOKENS = Counter(
    "eduguide_ai_tokens_total", "Tokens sent to and received from the AI.", ["provider", "tier", "kind"]
)
RATE_LIMITED = Counter("eduguide_rate_limited_total", "Requests refused by a rate limit.", ["limit"])


def ai_call(provider: str, tier: str, outcome: str, *, input_tokens: int = 0, output_tokens: int = 0) -> None:
    """One call to the AI. `outcome`: ok, declined (Claude refused), invalid (an answer we could not
    use) or failed."""
    AI_REQUESTS.labels(provider, tier, outcome).inc()
    if input_tokens:
        AI_TOKENS.labels(provider, tier, "input").inc(input_tokens)
    if output_tokens:
        AI_TOKENS.labels(provider, tier, "output").inc(output_tokens)


def serve(port: int) -> None:
    """Starts the metrics page on `port`, in a thread of this process: binding can take a while (the
    standard library looks up the computer's name), and start-up need not wait for it. 0 = off."""
    if port:
        threading.Thread(target=start_http_server, args=(port,), name="metrics", daemon=True).start()
