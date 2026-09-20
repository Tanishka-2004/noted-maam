import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("app.metrics")


class MetricsCollector:
    """Standardized metrics taxonomy collector supporting Prom-compliant serialization."""

    def __init__(self) -> None:
        self._counters: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._gauges: Dict[str, float] = {}

    def increment(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increments a counter metric."""
        key = self._format_key(name, labels)
        self._counters[key] = self._counters.get(key, 0.0) + value
        logger.info(f"METRIC_COUNTER: {key}={self._counters[key]}")

    def record_duration(self, name: str, value_ms: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Records duration into histogram buckets."""
        key = self._format_key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value_ms)
        logger.info(f"METRIC_HISTOGRAM: {key}={value_ms}ms")

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Sets value of gauge metric."""
        key = self._format_key(name, labels)
        self._gauges[key] = value
        logger.info(f"METRIC_GAUGE: {key}={value}")

    def _format_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_value(self, name: str) -> float:
        """Helper to get metric values for unit tests."""
        return self._counters.get(name, 0.0) or self._gauges.get(name, 0.0)

    def export_prometheus_format(self) -> str:
        """Serializes current metrics to the standard Prometheus exporter format."""
        lines = []
        
        # 1. Export Counters
        for key, val in self._counters.items():
            lines.append(f"{key} {val}")
            
        # 2. Export Gauges
        for key, val in self._gauges.items():
            lines.append(f"{key} {val}")

        # 3. Export Histograms (simulated summaries)
        for key, vals in self._histograms.items():
            count = len(vals)
            total = sum(vals)
            
            # Base name for labels mapping
            base_key = key
            if "{" in key:
                base_name = key.split("{")[0]
                label_part = key.split("{")[1].rstrip("}")
                lines.append(f'{base_name}_count{{{label_part}}} {count}')
                lines.append(f'{base_name}_sum{{{label_part}}} {total}')
            else:
                lines.append(f"{base_key}_count {count}")
                lines.append(f"{base_key}_sum {total}")

        return "\n".join(lines) + "\n"


# Global metrics collector instance
metrics_collector = MetricsCollector()
