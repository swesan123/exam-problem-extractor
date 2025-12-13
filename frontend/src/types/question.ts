export interface Question {
  id: string
  class_id: string
  question_text: string
  solution?: string
  metadata?: Record<string, unknown>
  source_image?: string
  created_at: string
  updated_at: string
  slideset?: string
  slide?: number
  topic?: string
  user_confidence?: 'confident' | 'uncertain' | 'not_confident'
  mock_exam_id?: string
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

export interface MockExam {
  id: string
  class_id: string
  title?: string
  instructions?: string
  exam_format?: string
  weighting_rules?: {
    pre_midterm_weight?: number
    post_midterm_weight?: number
    region_weights?: Record<string, number>
    slide_ranges?: Array<{start: number, end: number, weight: number}>
  }
  exam_metadata?: Record<string, any>
  questions: Question[]
  created_at: string
  updated_at: string
}

export interface ReferenceChunk {
  id: string
  slideset?: string
  slide_number?: number
  topic?: string
  exam_region?: 'pre' | 'post'
  auto_tags?: Record<string, any>
  user_overrides?: Record<string, any>
  // Merged view (for display)
  effective_metadata?: Record<string, any>
}

