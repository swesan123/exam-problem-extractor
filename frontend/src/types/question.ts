export interface Question {
  id: string
  class_id: string
  question_text: string
  solution?: string
  metadata?: Record<string, any>
  source_image?: string
  created_at: string
  updated_at: string
}

export interface GenerateResponse {
  question: string
  metadata: Record<string, any>
  processing_steps: string[]
  question_id?: string
  class_id?: string
}

