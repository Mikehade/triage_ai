from utils.logger import get_logger

logger = get_logger()


class NoopObservability:
    """
    No-op observability for local development without Phoenix.

    Swap in via the DI container when PHOENIX_MODE=noop.
    Implements the same interface as PhoenixObservability so
    startup code never needs to branch on observability mode.
    """

    def instrument(self) -> None:
        logger.info(
            "NoopObservability: instrumentation skipped. "
            "Set PHOENIX_MODE=cloud or PHOENIX_MODE=local to enable tracing."
        )

    def shutdown(self) -> None:
        pass