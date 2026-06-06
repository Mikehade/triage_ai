"""
Vertex AI Search (Discovery Engine) implementation of IKnowledgeStore.

Backed by a Vertex AI Data Store / Engine loaded with medical guidelines.
Fully aligned with the verified working knowledge_test.py script structure.
"""
import json
import os
import asyncio

from google.cloud import discoveryengine_v1 as discoveryengine
from google.api_core.client_options import ClientOptions
from google.oauth2 import service_account
from google.api_core import exceptions
from google.api_core.exceptions import GoogleAPIError

from src.infrastructure.knowledge.base import IKnowledgeStore
from utils.logger import get_logger

logger = get_logger()


class VertexKnowledgeStore(IKnowledgeStore):

    def __init__(
        self,
        project: str = None,
        location: str = None,
        datastore_id: str = None,  # Kept in signature for base class interface compliance
    ):
        # 1. Pull exact structural variables directly from environment, mimicking your script
        self._project_id = project or os.getenv("GCP_PROJECT")
        self._location = location or os.getenv("LOCATION", "global")
        
        # Explicit Engine ID handling mapping straight to your functional runtime variables
        self._engine_id = os.getenv("ENGINE_ID") or "clinical-copilot_1780771435229"
        
        self._service_account_json_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

        # 2. Set up client options based on location (Identical to your script)
        client_options = (
            ClientOptions(api_endpoint=f"{self._location}-discoveryengine.googleapis.com")
            if self._location != "global"
            else None
        )

        # 3. Set up authentication using the JSON string (Identical to your script)
        credentials = None
        if self._service_account_json_str:
            try:
                service_account_info = json.loads(self._service_account_json_str)
                credentials = service_account.Credentials.from_service_account_info(service_account_info)
                logger.info("VertexKnowledgeStore authenticated successfully with explicit Service Account.")
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing GOOGLE_SERVICE_ACCOUNT_JSON in production init: {e}")

        # 4. Create the client with credentials and options
        self._search_client = discoveryengine.SearchServiceClient(
            client_options=client_options,
            credentials=credentials
        )

        # The full resource name of the search app serving config
        self._serving_config = (
            f"projects/{self._project_id}/locations/{self._location}"
            f"/collections/default_collection/engines/{self._engine_id}"
            f"/servingConfigs/default_config"
        )

    async def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Semantic search replicating the configuration payloads from your working script.
        """
        try:
            # Replicating your exact content_search_spec structure from knowledge_test.py
            content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
                snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                    return_snippet=True
                ),
                summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
                    summary_result_count=5,
                    include_citations=True,
                    model_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
                        version="stable",
                    ),
                ),
            )

            # Replicating your exact request schema structure
            request = discoveryengine.SearchRequest(
                serving_config=self._serving_config,
                query=query,
                page_size=10,  # Matches working script page limit footprint
                content_search_spec=content_search_spec,
                query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
                    condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
                ),
                spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
                    mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
                ),
            )

            # Offload synchronous call to avoid blocking the async execution loop
            loop = asyncio.get_event_loop()
            page_result = await loop.run_in_executor(
                None,
                self._search_client.search,
                request,
            )

            results = []

            # 1. Capture the summary block if present so the LLM gets top-tier context instantly
            if hasattr(page_result, "summary") and page_result.summary and page_result.summary.summary_text:
                results.append({
                    "content": page_result.summary.summary_text,
                    "source": "Vertex Search Generative Summary",
                    "relevance": 1.0,
                })

            # 2. Loop over and parse the individual hits out of the response stream (Matches your print loop)
            for response in page_result:
                document = response.document
                content = ""
                
                if document.derived_struct_data:
                    snippets = document.derived_struct_data.get("snippets", [])
                    if snippets:
                        content = snippets[0].get("snippet", "")

                if not content and document.struct_data:
                    content = str(document.struct_data)

                # Capture title/link attributes cleanly like your test response properties
                source = "unknown"
                if document.derived_struct_data:
                    source = (
                        document.derived_struct_data.get("title", "")
                        or document.derived_struct_data.get("link", "")
                    )
                if not source and document.struct_data:
                    source = document.struct_data.get("source", "") or document.name

                if content:
                    results.append({
                        "content": content,
                        "source": source,
                        "relevance": float(response.rank_signals.semantic_similarity_score) 
                        if hasattr(response, "rank_signals") and hasattr(response.rank_signals, "semantic_similarity_score") 
                        else 1.0,
                    })

            logger.info(f"VertexKnowledgeStore: Extracted {len(results)} structured documents for triage agent processing.")
            return results

        except (exceptions.InternalServerError, exceptions.FailedPrecondition) as e:
            logger.warning(f"VertexKnowledgeStore encountered a transient endpoint exception: {e}. Falling back safely.")
            return []
            
        except exceptions.NotFound as e:
            logger.error(f"Engine identification string invalid on remote path: {self._serving_config}. Details: {e}")
            return []
            
        except GoogleAPIError as e:
            logger.error(f"VertexKnowledgeStore execution connection failure: {e}", exc_info=True)
            raise
            
        except Exception as e:
            logger.error(f"VertexKnowledgeStore unhandled pipeline exception: {e}", exc_info=True)
            raise

    async def get_drug_interactions(
        self,
        medications: list[str],
    ) -> list[dict]:
        """
        Formulary lookup for drug interactions.
        """
        if not medications:
            return []

        query = f"drug interactions contraindications: {', '.join(medications)}"

        try:
            return await self.search(query=query, top_k=5)
        except Exception as e:
            logger.warning(f"VertexKnowledgeStore.get_drug_interactions fell back: {e}.")
            return []