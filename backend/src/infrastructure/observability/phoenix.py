"""
Phoenix Observability.
Configures OpenInference instrumentation and registers the Phoenix OTEL
tracer provider.

For Phoenix Cloud, authentication is handled entirely via the PHOENIX_API_KEY
environment variable — register() picks it up automatically and adds the
correct Authorization header. Do not pass api_key in headers manually.

The endpoint must be the fully qualified HTTP traces endpoint:
  https://app.phoenix.arize.com/v1/traces
Not the base domain — register() does not append the path automatically
when endpoint is passed explicitly.
"""
import os

from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from phoenix.otel import register
from opentelemetry.sdk.trace import TracerProvider

from utils.logger import get_logger

logger = get_logger()


class PhoenixObservability:

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

        Authentication for Phoenix Cloud works via PHOENIX_API_KEY env var —
        register() reads it automatically and sets the Authorization header.
        We ensure the env var is set before calling register() in case it
        was passed via config rather than the shell environment.
        """
        if self._api_key:
            os.environ["PHOENIX_API_KEY"] = self._api_key

        # Ensure endpoint points to the HTTP traces path, not just the base URL.
        # register() does not append /v1/traces automatically when endpoint
        # is passed explicitly.
        endpoint = self._endpoint
        if not endpoint.endswith("/v1/traces"):
            endpoint = endpoint.rstrip("/") + "/v1/traces"

        try:
            self._tracer_provider = register(
                project_name=self._project_name,
                endpoint=endpoint,
                batch=True,   # BatchSpanProcessor — required for production
            )
            GoogleADKInstrumentor().instrument(
                tracer_provider=self._tracer_provider
            )
            logger.info(
                f"PhoenixObservability: instrumentation active. "
                f"project='{self._project_name}' endpoint='{endpoint}'"
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