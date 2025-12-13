export interface Class {
  id: string
  name: string
  description?: string
  subject?: string
  exam_format?: string
  created_at: string
  updated_at: string
}

export interface ClassCreate {
  name: string
  description?: string
  subject?: string
}

export interface ClassUpdate {
  name?: string
  description?: string
  subject?: string
}

export interface ClassListResponse {
  classes: Class[]
  total: number
}

