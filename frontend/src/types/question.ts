export interface Question {
  id: string
  class_id: string
  question_text: string
  solution?: string
  metadata?: Record<string, unknown>
  source_image?: string
  created_at: string
  updated_at: string
}

export interface ReferenceCitation {
  source_file: string
  chunk_id: string
  reference_type: string
  score: number
}

export interface GenerateResponse {
  question: string
  metadata: Record<string, unknown>
  processing_steps: string[]
  question_id?: string
  class_id?: string
  references_used?: {
    assessment?: ReferenceCitation[]
    lecture?: ReferenceCitation[]
  }
}

