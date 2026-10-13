from types import SimpleNamespace

from aforix.batch.metrics import MetricsCollector


class ProcessUnavailable(Exception):
    pass


class UnavailablePsutil:
    Error = ProcessUnavailable

    @staticmethod
    def Process():
        raise ProcessUnavailable


def test_metrics_degrade_when_process_is_unavailable_at_start() -> None:
    collector = MetricsCollector()
    collector._psutil = UnavailablePsutil

    collector.start()
    metrics = collector.stop()

    assert metrics.duration_sec is not None
    assert metrics.metrics_available is False


class VanishingPsutil:
    Error = ProcessUnavailable
    calls = 0

    @classmethod
    def Process(cls):
        cls.calls += 1
        if cls.calls > 1:
            raise ProcessUnavailable

        return SimpleNamespace(
            memory_info=lambda: SimpleNamespace(rss=1024),
            cpu_percent=lambda interval=None: 0.0,
        )


def test_metrics_degrade_when_process_disappears_at_stop() -> None:
    VanishingPsutil.calls = 0
    collector = MetricsCollector()
    collector._psutil = VanishingPsutil

    collector.start()
    metrics = collector.stop()

    assert metrics.duration_sec is not None
    assert metrics.metrics_available is False
