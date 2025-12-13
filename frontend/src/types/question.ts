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
  coverage?: number
}

export interface GenerateResponse {
  question?: string
  questions?: string[]
  metadata: Record<string, unknown>
  processing_steps: string[]
  question_id?: string
  class_id?: string
  references_used?: {
    assessment?: ReferenceCitation[]
    lecture?: ReferenceCitation[]
  }
  mock_exam_id?: string
  weighting_rules?: {
    pre_midterm_weight?: number
    post_midterm_weight?: number
    region_weights?: Record<string, number>
    slide_ranges?: Array<{start: number, end: number, weight: number}>
  }
}

