import apiClient from './api'

export interface JobStatus {
  job_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  total_files: number
  processed_files: number
  failed_files: number
  file_statuses: Record<string, FileStatus>
  error_message: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
}

export interface FileStatus {
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  error?: string | null
}

export interface UploadJobResponse {
  job_id: string
  status: string
  total_files: number
  message: string
}

export interface ClassJobsResponse {
  class_id: string
  jobs: Array<{
    job_id: string
    status: string
    progress: number
    total_files: number
    processed_files: number
    failed_files: number
    created_at: string
    completed_at: string | null
  }>
}

export const jobService = {
  async uploadReferenceContent(
    classId: string,
    files: File[],
    examSource?: string,
    examType?: string
  ): Promise<UploadJobResponse> {
    const formData = new FormData()
    formData.append('class_id', classId)
    if (examSource) formData.append('exam_source', examSource)
    if (examType) formData.append('exam_type', examType)
    
    files.forEach((file) => {
      formData.append('files', file)
    })

    const response = await apiClient.post<UploadJobResponse>(
      '/api/reference-content/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )
    return response.data
  },

  async getJobStatus(jobId: string): Promise<JobStatus> {
    const response = await apiClient.get<JobStatus>(`/api/reference-content/jobs/${jobId}`)
    return response.data
  },

  async listClassJobs(classId: string): Promise<ClassJobsResponse> {
    const response = await apiClient.get<ClassJobsResponse>(
      `/api/reference-content/jobs/class/${classId}`
    )
    return response.data
  },
}

