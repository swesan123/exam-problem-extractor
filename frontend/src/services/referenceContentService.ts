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
    reference_type?: string
    source_file?: string
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

  async update(
    chunkId: string,
    updates: {
      exam_region?: 'pre' | 'post' | null
      slideset?: string
      slide_number?: number
      topic?: string
    }
  ): Promise<ReferenceContentItem> {
    const response = await apiClient.patch<ReferenceContentItem>(
      `/api/reference-content/${chunkId}`,
      updates
    )
    return response.data
  },
}

