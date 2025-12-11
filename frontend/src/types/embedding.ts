export interface EmbeddingMetadata {
  source: string
  chunk_id: string
  page?: number
  timestamp?: string
  exam_type?: string
  class_id?: string
  [key: string]: unknown
}

export interface EmbeddingRequest {
  text: string
  metadata?: EmbeddingMetadata
}

export interface EmbeddingResponse {
  embedding_id: string
  status: string
  vector_dimension: number
}

