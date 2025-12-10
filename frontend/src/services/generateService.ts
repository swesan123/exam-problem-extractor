import apiClient from './api'
import { GenerateResponse } from '../types/question'

export interface GenerateRequest {
  ocr_text?: string
  image_file?: File
  retrieved_context?: string
  include_solution?: boolean
  class_id?: string
}

export const generateService = {
  async generate(data: GenerateRequest): Promise<GenerateResponse> {
    const formData = new FormData()

    if (data.ocr_text) {
      formData.append('ocr_text', data.ocr_text)
    }
    if (data.image_file) {
      formData.append('image_file', data.image_file)
    }
    if (data.retrieved_context) {
      formData.append('retrieved_context', data.retrieved_context)
    }
    if (data.include_solution !== undefined) {
      formData.append('include_solution', String(data.include_solution))
    }
    if (data.class_id) {
      formData.append('class_id', data.class_id)
    }

    const response = await apiClient.post<GenerateResponse>('/generate', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
}

