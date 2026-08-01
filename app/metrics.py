from collections import Counter
from time import perf_counter


class Metrics:
    _buckets = (0.005, 0.025, 0.1, 0.25, 0.5)

    def __init__(self) -> None:
        self.requests = Counter()
        self.duration_count = 0
        self.duration_sum = 0.0
        self.duration_buckets = Counter()

    def observe_request(self, method: str, path: str, status: int, duration: float) -> None:
        self.requests[(method, path, status)] += 1
        self.duration_count += 1
        self.duration_sum += duration
        for bucket in self._buckets:
            if duration <= bucket:
                self.duration_buckets[bucket] += 1
                break

    def render(self) -> str:
        lines = [
            "# HELP flowforge_http_requests_total Total HTTP requests.",
            "# TYPE flowforge_http_requests_total counter",
        ]
        for (method, path, status), count in sorted(self.requests.items()):
            lines.append(
                f'flowforge_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
            )
        lines.extend(
            [
                "# HELP flowforge_http_request_duration_seconds HTTP request duration.",
                "# TYPE flowforge_http_request_duration_seconds histogram",
                f"flowforge_http_request_duration_seconds_count {self.duration_count}",
                f"flowforge_http_request_duration_seconds_sum {self.duration_sum:.6f}",
            ]
        )
        cumulative = 0
        for bucket in self._buckets:
            cumulative += self.duration_buckets[bucket]
            lines.append(
                f'flowforge_http_request_duration_seconds_bucket{{le="{bucket}"}} {cumulative}'
            )
        lines.append(
            f'flowforge_http_request_duration_seconds_bucket{{le="+Inf"}} {self.duration_count}'
        )
        return "\n".join(lines) + "\n"


metrics = Metrics()


def now() -> float:
    return perf_counter()
