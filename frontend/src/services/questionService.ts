import apiClient from './api'
import { Question } from '../types/question'

export interface QuestionListResponse {
  questions: Question[]
  total: number
  skip: number
  limit: number
}

export const questionService = {
  async getByClass(classId: string): Promise<QuestionListResponse> {
    const response = await apiClient.get<QuestionListResponse>(
      `/api/questions/classes/${classId}/questions`
    )
    return response.data
  },

  async delete(questionId: string): Promise<void> {
    await apiClient.delete(`/api/questions/${questionId}`)
  },

  async download(
    questionId: string,
    format: 'txt' | 'pdf' | 'docx' | 'json' = 'txt',
    includeSolution: boolean = false
  ): Promise<void> {
    const response = await apiClient.get(
      `/api/questions/${questionId}/download`,
      {
        params: { format, include_solution: includeSolution },
        responseType: 'blob',
      }
    )
    const blob = response.data
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `question_${questionId}.${format}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  },
}

