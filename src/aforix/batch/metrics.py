from dataclasses import dataclass


@dataclass(slots=True)
class StepMetrics:
    duration_sec: float | None = None
    cpu_avg_percent: float | None = None
    cpu_max_percent: float | None = None
    ram_peak_mb: float | None = None
    input_size_mb: float | None = None
    output_size_mb: float | None = None
    rows_processed: int | None = None
