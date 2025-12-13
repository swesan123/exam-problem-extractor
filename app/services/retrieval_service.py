"""Retrieval service for semantic search over vector database."""

from typing import List, Optional

from openai import OpenAI

from app.models.retrieval_models import RetrievedChunk
from app.services.embedding_service import EmbeddingService


class RetrievalService:
    """Service for retrieving similar content from vector database."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        openai_client: Optional[OpenAI] = None,
    ):
        """
        Initialize retrieval service.

        Args:
            embedding_service: EmbeddingService instance for generating query embeddings
            openai_client: OpenAI client instance (optional, uses embedding_service's client)
        """
        self.embedding_service = embedding_service
        self.client = openai_client or embedding_service.client

    def retrieve(
        self,
        query: str,
        top_k: int,
        class_id: Optional[str] = None,
        reference_type: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieve top_k similar chunks without scores.

        Args:
            query: Query text
            top_k: Number of results to retrieve
            class_id: Optional class ID to filter by
            reference_type: Optional reference type to filter by (e.g., assessment, lecture)

        Returns:
            List of RetrievedChunk objects
        """
        return self.retrieve_with_scores(query, top_k, class_id, reference_type)

    def retrieve_with_scores(
        self,
        query: str,
        top_k: int,
        class_id: Optional[str] = None,
        reference_type: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieve top_k similar chunks with similarity scores.

        Args:
            query: Query text
            top_k: Number of results to retrieve
            class_id: Optional class ID to filter by
            reference_type: Optional reference type to filter by (e.g., assessment, lecture)

        Returns:
            List of RetrievedChunk objects sorted by score (descending)

        Raises:
            Exception: If retrieval fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if top_k < 1 or top_k > 100:
            raise ValueError("top_k must be between 1 and 100")

        try:
            # Generate query embedding
            query_embedding = self.embedding_service.generate_embedding(query)

            # Build where clause for filtering
            where_clause = None
            if class_id or reference_type:
                where_clause = {}
                if class_id:
                    where_clause["class_id"] = class_id
                if reference_type:
                    where_clause["reference_type"] = reference_type

            # Perform similarity search
            collection = self.embedding_service.collection
            query_kwargs = {
                "query_embeddings": [query_embedding],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"],
            }
            if where_clause:
                query_kwargs["where"] = where_clause

            results = collection.query(**query_kwargs)

            # Convert to RetrievedChunk objects
            retrieved_chunks = []
            if results["ids"] and len(results["ids"][0]) > 0:
                for i in range(len(results["ids"][0])):
                    # ChromaDB returns distances (lower is better), convert to similarity score
                    distance = results["distances"][0][i]
                    # Convert distance to similarity (1 - normalized distance)
                    # Assuming cosine distance, similarity = 1 - distance
                    score = max(0.0, min(1.0, 1.0 - distance))

                    chunk = RetrievedChunk(
                        text=results["documents"][0][i],
                        score=score,
                        metadata=results["metadatas"][0][i] or {},
                        chunk_id=results["ids"][0][i],
                    )
                    retrieved_chunks.append(chunk)

            # Sort by score (descending) - ChromaDB should already return sorted, but ensure it
            retrieved_chunks.sort(key=lambda x: x.score, reverse=True)

            return retrieved_chunks

        except Exception as e:
            raise Exception(f"Retrieval failed: {str(e)}") from e
