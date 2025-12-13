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
        weighting_rules: Optional[Dict] = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieve top_k similar chunks without scores.

        Args:
            query: Query text
            top_k: Number of results to retrieve
            class_id: Optional class ID to filter by
            reference_type: Optional reference type to filter by (e.g., assessment, lecture)
            weighting_rules: Optional weighting rules dictionary for dynamic weighting

        Returns:
            List of RetrievedChunk objects
        """
        return self.retrieve_with_scores(query, top_k, class_id, reference_type, weighting_rules)

    def retrieve_with_scores(
        self,
        query: str,
        top_k: int,
        class_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        weighting_rules: Optional[Dict] = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieve top_k similar chunks with similarity scores.

        Args:
            query: Query text
            top_k: Number of results to retrieve
            class_id: Optional class ID to filter by
            reference_type: Optional reference type to filter by (e.g., assessment, lecture)
            weighting_rules: Optional weighting rules dictionary for dynamic weighting:
                {
                    "pre_midterm_weight": float,
                    "post_midterm_weight": float,
                    "region_weights": {"pre": float, "post": float},
                    "slide_ranges": [{"start": int, "end": int, "weight": float}, ...]
                }

        Returns:
            List of RetrievedChunk objects sorted by weighted score (descending)

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
            # ChromaDB requires using operators ($and, $or) when there are multiple conditions
            where_clause = None
            if class_id or reference_type:
                if class_id and reference_type:
                    # Multiple conditions need $and operator
                    where_clause = {
                        "$and": [
                            {"class_id": class_id},
                            {"reference_type": reference_type}
                        ]
                    }
                elif class_id:
                    where_clause = {"class_id": class_id}
                elif reference_type:
                    where_clause = {"reference_type": reference_type}

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

            # Apply weighting if rules provided
            if weighting_rules:
                retrieved_chunks = self._apply_weighting(retrieved_chunks, weighting_rules)

            # Sort by score (descending) - ChromaDB should already return sorted, but ensure it
            retrieved_chunks.sort(key=lambda x: x.score, reverse=True)

            return retrieved_chunks

        except Exception as e:
            raise Exception(f"Retrieval failed: {str(e)}") from e

    def _apply_weighting(
        self, chunks: List[RetrievedChunk], weighting_rules: Dict
    ) -> List[RetrievedChunk]:
        """
        Apply weighting rules to retrieved chunks.

        Args:
            chunks: List of RetrievedChunk objects
            weighting_rules: Weighting rules dictionary

        Returns:
            List of RetrievedChunk objects with weighted scores
        """
        weighted_chunks = []

        # Get region weights
        region_weights = weighting_rules.get("region_weights")
        if not region_weights:
            # Fallback to pre/post weights
            pre_weight = weighting_rules.get("pre_midterm_weight", 1.0)
            post_weight = weighting_rules.get("post_midterm_weight", 1.0)
            region_weights = {"pre": pre_weight, "post": post_weight}

        # Get slide ranges if specified
        slide_ranges = weighting_rules.get("slide_ranges", [])

        for chunk in chunks:
            weighted_score = chunk.score
            metadata = chunk.metadata or {}

            # Apply region-based weighting
            exam_region = metadata.get("exam_region")
            if exam_region in region_weights:
                weighted_score *= region_weights[exam_region]

            # Apply slide range-based weighting (takes precedence if both exist)
            if slide_ranges:
                slide_number = metadata.get("slide_number")
                if slide_number is not None:
                    for range_spec in slide_ranges:
                        start = range_spec.get("start", 0)
                        end = range_spec.get("end", float("inf"))
                        weight = range_spec.get("weight", 1.0)
                        if start <= slide_number <= end:
                            weighted_score *= weight
                            break  # Use first matching range

            # Create new chunk with weighted score
            weighted_chunk = RetrievedChunk(
                text=chunk.text,
                score=min(1.0, max(0.0, weighted_score)),  # Clamp to [0, 1]
                metadata=chunk.metadata,
                chunk_id=chunk.chunk_id,
            )
            weighted_chunks.append(weighted_chunk)

        return weighted_chunks
