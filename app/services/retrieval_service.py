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

    def retrieve(self, query: str, top_k: int, class_id: Optional[str] = None) -> List[RetrievedChunk]:
        """
        Retrieve top_k similar chunks without scores.

        Args:
            query: Query text
            top_k: Number of results to retrieve
            class_id: Optional class ID to filter results by

        Returns:
            List of RetrievedChunk objects
        """
        return self.retrieve_with_scores(query, top_k, class_id)

    def retrieve_with_scores(
        self, query: str, top_k: int, class_id: Optional[str] = None
    ) -> List[RetrievedChunk]:
        """
        Retrieve top_k similar chunks with similarity scores.

        Args:
            query: Query text
            top_k: Number of results to retrieve
            class_id: Optional class ID to filter results by (only returns chunks from this class)

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

            # Build query filter if class_id provided
            where_filter = None
            if class_id:
                where_filter = {"class_id": class_id}

            # Perform similarity search
            collection = self.embedding_service.collection
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,  # Filter by class_id if provided
                include=["documents", "metadatas", "distances"],
            )

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
