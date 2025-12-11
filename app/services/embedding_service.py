"""Embedding service for generating and storing text embeddings."""

from typing import Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI

from app.config import settings
from app.utils.chunking import smart_chunk


class EmbeddingService:
    """Service for generating and storing text embeddings."""

    def __init__(
        self,
        openai_client: Optional[OpenAI] = None,
        vector_db_client: Optional[chromadb.ClientAPI] = None,
    ):
        """
        Initialize embedding service.

        Args:
            openai_client: OpenAI client instance
            vector_db_client: ChromaDB client instance
        """
        self.client = openai_client or OpenAI(api_key=settings.openai_api_key)
        self.embedding_model = settings.embedding_model

        # Initialize vector database
        if vector_db_client:
            self.vector_db = vector_db_client
        else:
            self.vector_db = chromadb.PersistentClient(
                path=str(settings.vector_db_path),
                settings=ChromaSettings(anonymized_telemetry=False),
            )

        # Get or create collection
        self.collection = self.vector_db.get_or_create_collection(
            name="exam_embeddings",
            metadata={"embedding_model": self.embedding_model},
        )

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            Exception: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"Failed to generate embedding: {str(e)}") from e

    def store_embedding(self, text: str, embedding: List[float], metadata: Dict) -> str:
        """
        Store embedding in vector database.

        Args:
            text: Original text
            embedding: Embedding vector
            metadata: Metadata dictionary

        Returns:
            Embedding ID (chunk_id from metadata)
        """
        chunk_id = metadata.get(
            "chunk_id", f"chunk_{len(self.collection.get()['ids'])}"
        )

        # Store in ChromaDB
        self.collection.add(
            ids=[chunk_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
        )

        return chunk_id

    def batch_store(self, texts: List[str], metadata_list: List[Dict]) -> List[str]:
        """
        Store multiple embeddings efficiently.

        Args:
            texts: List of texts to embed and store
            metadata_list: List of metadata dictionaries

        Returns:
            List of embedding IDs
        """
        if len(texts) != len(metadata_list):
            raise ValueError("Texts and metadata lists must have the same length")

        # Generate embeddings in batch
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=texts,
            )
            embeddings = [item.embedding for item in response.data]
        except Exception as e:
            raise Exception(f"Failed to generate batch embeddings: {str(e)}") from e

        # Extract chunk IDs
        chunk_ids = [
            meta.get("chunk_id", f"chunk_{i}") for i, meta in enumerate(metadata_list)
        ]

        # Store in ChromaDB
        self.collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadata_list,
        )

        return chunk_ids

    def store_text_with_chunking(
        self, text: str, metadata: Dict, max_chunk_size: int = 1000
    ) -> List[str]:
        """
        Store text with automatic chunking if needed.

        Args:
            text: Text to store
            metadata: Base metadata (chunk_id will be appended)
            max_chunk_size: Maximum chunk size in characters

        Returns:
            List of chunk IDs
        """
        # Chunk text if needed
        chunks = smart_chunk(text, max_chunk_size)

        if len(chunks) == 1:
            # Single chunk, use simple storage
            embedding = self.generate_embedding(chunks[0])
            return [self.store_embedding(chunks[0], embedding, metadata)]
        else:
            # Multiple chunks, use batch storage
            metadata_list = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = metadata.copy()
                chunk_metadata["chunk_id"] = f"{metadata.get('chunk_id', 'chunk')}_{i}"
                metadata_list.append(chunk_metadata)

            return self.batch_store(chunks, metadata_list)

    def list_embeddings_by_class(self, class_id: str) -> List[Dict]:
        """
        List all embeddings for a specific class.

        Args:
            class_id: Class ID to filter by

        Returns:
            List of dictionaries with chunk_id, text, and metadata
        """
        try:
            # Get all embeddings from collection
            all_data = self.collection.get(include=["documents", "metadatas"])
            
            # Filter by class_id in metadata
            results = []
            for i, metadata in enumerate(all_data["metadatas"]):
                if metadata and metadata.get("class_id") == class_id:
                    results.append({
                        "chunk_id": all_data["ids"][i],
                        "text": all_data["documents"][i],
                        "metadata": metadata,
                    })
            
            return results
        except Exception as e:
            raise Exception(f"Failed to list embeddings by class: {str(e)}") from e

    def delete_embedding(self, chunk_id: str) -> bool:
        """
        Delete an embedding by chunk_id.

        Args:
            chunk_id: Chunk ID to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            # Check if chunk exists
            existing = self.collection.get(ids=[chunk_id])
            if not existing["ids"]:
                return False
            
            # Delete the chunk
            self.collection.delete(ids=[chunk_id])
            return True
        except Exception as e:
            raise Exception(f"Failed to delete embedding: {str(e)}") from e
