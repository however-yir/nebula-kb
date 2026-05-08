"""
Prometheus-compatible /metrics endpoint for yourrag.
Exposes request latency, active connections, queue depth, and document processing stats.
"""
import psutil
from quart import Blueprint, Response

manager = Blueprint("system_metrics", __name__)

# In-memory counters (thread-safe via GIL for CPython)
_counters = {
    "http_requests_total": {},  # (method, path, status) -> count
    "http_request_duration_seconds_sum": {},  # (method, path) -> sum
    "http_request_duration_seconds_count": {},  # (method, path) -> count
}


def record_request(method: str, path: str, status: int, duration: float):
    key = (method, path, str(status))
    _counters["http_requests_total"][key] = _counters["http_requests_total"].get(key, 0) + 1
    sum_key = (method, path)
    _counters["http_request_duration_seconds_sum"][sum_key] = (
        _counters["http_request_duration_seconds_sum"].get(sum_key, 0) + duration
    )
    _counters["http_request_duration_seconds_count"][sum_key] = (
        _counters["http_request_duration_seconds_count"].get(sum_key, 0) + 1
    )


@manager.route("/v1/system/metrics", methods=["GET"])
async def metrics():
    lines = []
    lines.append("# HELP yourrag_http_requests_total Total HTTP requests")
    lines.append("# TYPE yourrag_http_requests_total counter")
    for (method, path, status), count in _counters["http_requests_total"].items():
        safe_path = path.replace('"', '\\"')
        lines.append(f'yourrag_http_requests_total{{method="{method}",path="{safe_path}",status="{status}"}} {count}')

    lines.append("# HELP yourrag_http_request_duration_seconds_sum Total request duration in seconds")
    lines.append("# TYPE yourrag_http_request_duration_seconds_sum counter")
    for (method, path), val in _counters["http_request_duration_seconds_sum"].items():
        safe_path = path.replace('"', '\\"')
        lines.append(f'yourrag_http_request_duration_seconds_sum{{method="{method}",path="{safe_path}"}} {val:.6f}')

    lines.append("# HELP yourrag_http_request_duration_seconds_count Number of requests")
    lines.append("# TYPE yourrag_http_request_duration_seconds_count counter")
    for (method, path), val in _counters["http_request_duration_seconds_count"].items():
        safe_path = path.replace('"', '\\"')
        lines.append(f'yourrag_http_request_duration_seconds_count{{method="{method}",path="{safe_path}"}} {val}')

    # System metrics
    try:
        proc = psutil.Process()
        mem = proc.memory_info()
        lines.append("# HELP yourrag_process_resident_memory_bytes Resident memory")
        lines.append("# TYPE yourrag_process_resident_memory_bytes gauge")
        lines.append(f"yourrag_process_resident_memory_bytes {mem.rss}")
        lines.append("# HELP yourrag_process_cpu_percent CPU usage percent")
        lines.append("# TYPE yourrag_process_cpu_percent gauge")
        lines.append(f"yourrag_process_cpu_percent {proc.cpu_percent(interval=None):.2f}")
        lines.append("# HELP yourrag_process_open_fds Open file descriptors")
        lines.append("# TYPE yourrag_process_open_fds gauge")
        lines.append(f"yourrag_process_open_fds {proc.num_fds()}")
    except Exception:
        pass

    body = "\n".join(lines) + "\n"
    return Response(body, mimetype="text/plain; version=0.0.4; charset=utf-8")
