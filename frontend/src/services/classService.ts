import apiClient from './api'
import { Class, ClassCreate, ClassUpdate, ClassListResponse } from '../types/class'

export const classService = {
  async getAll(): Promise<ClassListResponse> {
    const response = await apiClient.get<ClassListResponse>('/api/classes')
    return response.data
  },

  async getById(id: string): Promise<Class> {
    const response = await apiClient.get<Class>(`/api/classes/${id}`)
    return response.data
  },

  async create(data: ClassCreate): Promise<Class> {
    const response = await apiClient.post<Class>('/api/classes', data)
    return response.data
  },

  async update(id: string, data: ClassUpdate): Promise<Class> {
    const response = await apiClient.put<Class>(`/api/classes/${id}`, data)
    return response.data
  },

  async delete(id: string): Promise<void> {
    await apiClient.delete(`/api/classes/${id}`)
  },

  async updateExamFormat(id: string, examFormat: string): Promise<Class> {
    const formData = new FormData()
    formData.append('exam_format', examFormat)
    const response = await apiClient.patch<Class>(`/api/classes/${id}/exam-format`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
}

