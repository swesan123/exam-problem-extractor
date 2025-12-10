import api from './api'
import { EmbeddingRequest, EmbeddingResponse } from '../types/embedding'

export const embedService = {
  async embedText(request: EmbeddingRequest): Promise<EmbeddingResponse> {
    const response = await api.post<EmbeddingResponse>('/embed', request)
    return response.data
  },
}

