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
}

