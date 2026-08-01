from app.metrics import Metrics


def test_metrics_render_prometheus_histogram() -> None:
    metrics = Metrics()
    metrics.observe_request("GET", "/health", 200, 0.01)
    metrics.observe_request("GET", "/health", 200, 0.2)

    output = metrics.render()

    assert 'flowforge_http_requests_total{method="GET",path="/health",status="200"} 2' in output
    assert 'flowforge_http_request_duration_seconds_bucket{le="0.025"} 1' in output
    assert 'flowforge_http_request_duration_seconds_bucket{le="+Inf"} 2' in output
