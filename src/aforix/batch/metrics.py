from dataclasses import asdict, dataclass
from time import perf_counter


@dataclass(slots=True)
class StepMetrics:
    duration_sec: float | None = None
    cpu_start_percent: float | None = None
    cpu_end_percent: float | None = None
    ram_start_mb: float | None = None
    ram_end_mb: float | None = None
    ram_peak_mb: float | None = None
    input_size_mb: float | None = None
    output_size_mb: float | None = None
    rows_processed: int | None = None
    metrics_available: bool = False


class MetricsCollector:
    """Collect lightweight step performance metrics.

    psutil is optional. If it is not installed, collection degrades gracefully.
    """

    def __init__(self) -> None:
        self._psutil = self._load_psutil()
        self._start_time: float | None = None
        self._ram_start_mb: float | None = None
        self._cpu_start_percent: float | None = None

    def start(self) -> None:
        self._start_time = perf_counter()

        if self._psutil is None:
            return

        process = self._psutil.Process()
        self._ram_start_mb = self._bytes_to_mb(process.memory_info().rss)
        self._cpu_start_percent = process.cpu_percent(interval=None)

    def stop(self) -> StepMetrics:
        duration_sec = None
        if self._start_time is not None:
            duration_sec = round(perf_counter() - self._start_time, 4)

        if self._psutil is None:
            return StepMetrics(
                duration_sec=duration_sec,
                metrics_available=False,
            )

        process = self._psutil.Process()
        ram_end_mb = self._bytes_to_mb(process.memory_info().rss)
        cpu_end_percent = process.cpu_percent(interval=None)

        return StepMetrics(
            duration_sec=duration_sec,
            cpu_start_percent=self._cpu_start_percent,
            cpu_end_percent=cpu_end_percent,
            ram_start_mb=self._ram_start_mb,
            ram_end_mb=ram_end_mb,
            ram_peak_mb=max(
                value
                for value in (self._ram_start_mb, ram_end_mb)
                if value is not None
            ),
            metrics_available=True,
        )

    def _load_psutil(self):
        try:
            import psutil
        except ImportError:
            return None

        return psutil

    def _bytes_to_mb(self, value: int) -> float:
        return round(value / (1024 * 1024), 4)


def metrics_to_dict(metrics: StepMetrics) -> dict:
    return asdict(metrics)
