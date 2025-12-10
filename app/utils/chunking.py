"""Text chunking utilities."""
from typing import List


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into chunks with overlap.

    Args:
        text: Text to chunk
        chunk_size: Maximum size of each chunk in characters
        overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks
    """
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # Try to break at word boundary if not at end
        if end < len(text):
            # Find last space in the chunk
            last_space = chunk.rfind(" ")
            if last_space > chunk_size * 0.8:  # If space is in last 20% of chunk
                chunk = chunk[:last_space]
                end = start + last_space

        chunks.append(chunk.strip())

        # Move start position with overlap
        start = end - overlap
        if start >= len(text):
            break

    return chunks


def chunk_by_sentences(text: str, max_chunk_size: int = 1000) -> List[str]:
    """
    Split text into chunks by sentences, respecting max_chunk_size.

    Args:
        text: Text to chunk
        max_chunk_size: Maximum size of each chunk in characters

    Returns:
        List of text chunks
    """
    if not text:
        return []

    # Split by sentence endings
    sentences = re.split(r"([.!?]\s+)", text)
    # Recombine sentences with their punctuation
    sentences = ["".join(sentences[i : i + 2]) for i in range(0, len(sentences) - 1, 2)]
    if len(sentences) % 2 == 1:
        sentences.append(sentences[-1])

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # If adding this sentence would exceed max size, start new chunk
        if current_chunk and len(current_chunk) + len(sentence) + 1 > max_chunk_size:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence

    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks if chunks else [text]


def smart_chunk(text: str, max_size: int = 1000) -> List[str]:
    """
    Intelligently chunk text preserving context and meaning.

    This function tries to preserve sentence boundaries and paragraph
    structure while respecting the max_size limit.

    Args:
        text: Text to chunk
        max_size: Maximum size of each chunk in characters

    Returns:
        List of text chunks
    """
    if not text:
        return []

    if len(text) <= max_size:
        return [text]

    # First, try to split by paragraphs
    paragraphs = text.split("\n\n")

    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        # If paragraph fits, add it
        if len(paragraph) <= max_size:
            if current_chunk and len(current_chunk) + len(paragraph) + 2 <= max_size:
                current_chunk += "\n\n" + paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph
        else:
            # Paragraph is too large, use sentence-based chunking
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            # Chunk the large paragraph by sentences
            para_chunks = chunk_by_sentences(paragraph, max_size)
            chunks.extend(para_chunks)

    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks if chunks else [text]


# Import re for sentence splitting
import re

