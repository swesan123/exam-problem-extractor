import apiClient from './api'

export interface ReferenceContentItem {
  chunk_id: string
  text: string
  metadata: {
    source?: string
    exam_type?: string
    class_id?: string
    page?: number
    chunk_id?: string
    timestamp?: string
  }
}

export interface ReferenceContentResponse {
  class_id: string
  items: ReferenceContentItem[]
  count: number
}

export const referenceContentService = {
  async getByClass(classId: string): Promise<ReferenceContentResponse> {
    const response = await apiClient.get<ReferenceContentResponse>(
      `/api/reference-content/classes/${classId}`
    )
    return response.data
  },

  async delete(chunkId: string): Promise<void> {
    await apiClient.delete(`/api/reference-content/${chunkId}`)
  },
}

