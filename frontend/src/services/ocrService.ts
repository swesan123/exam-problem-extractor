import api from './api'

export interface OCRResponse {
  text: string
  confidence?: number
  processing_time_ms?: number
}

export const ocrService = {
  async extractText(file: File): Promise<OCRResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post<OCRResponse>('/ocr', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
}

