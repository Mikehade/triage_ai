from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from phoenix.otel import register
from opentelemetry.sdk.trace import TracerProvider

from utils.logger import get_logger

logger = get_logger()


class PhoenixObservability:
    """
    Configures OpenInference instrumentation and registers the
    Phoenix OTEL tracer provider.

    Called once at startup in main.py — after this, every ADK
    tool call is automatically traced with zero manual span creation.

    Switching between Phoenix Cloud and local Phoenix is controlled
    entirely by the endpoint and api_key passed at construction.
    """

    def __init__(
        self,
        project_name: str,
        endpoint: str,
        api_key: str | None = None,
    ):
        self._project_name = project_name
        self._endpoint = endpoint
        self._api_key = api_key
        self._tracer_provider: TracerProvider | None = None

    def instrument(self) -> None:
        """
        Register the Phoenix tracer and instrument ADK.
        Must be called before any ADK agent runs.
        """
        headers = {}
        if self._api_key:
            headers["api_key"] = self._api_key

        try:
            self._tracer_provider = register(
                project_name=self._project_name,
                endpoint=self._endpoint,
                headers=headers,
            )
            GoogleADKInstrumentor().instrument(
                tracer_provider=self._tracer_provider
            )
            logger.info(
                f"PhoenixObservability: instrumentation active. "
                f"project='{self._project_name}' endpoint='{self._endpoint}'"
            )
        except Exception as e:
            logger.error(
                f"PhoenixObservability: failed to initialise: {e}. "
                "Traces will not be collected.",
                exc_info=True,
            )
            raise

    def shutdown(self) -> None:
        if self._tracer_provider:
            try:
                self._tracer_provider.shutdown()
                logger.info("PhoenixObservability: tracer provider shut down.")
            except Exception as e:
                logger.warning(f"PhoenixObservability: shutdown error: {e}")