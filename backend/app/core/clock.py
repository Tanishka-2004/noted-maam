import datetime

class Clock:
    """
    Clock provider abstraction allowing timezone-aware datetime resolution.
    Can be overridden in tests to enable deterministic execution of time-sensitive logic.
    """
    _provider = None

    @classmethod
    def set_provider(cls, provider) -> None:
        cls._provider = provider

    @classmethod
    def now(cls) -> datetime.datetime:
        if cls._provider is None:
            return datetime.datetime.now(datetime.timezone.utc)
        return cls._provider.now()
