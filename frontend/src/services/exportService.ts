import apiClient from './api'

export type ExportFormat = 'txt' | 'pdf' | 'docx' | 'json'

export const exportService = {
  async exportClass(classId: string, format: ExportFormat): Promise<Blob> {
    const response = await apiClient.get(`/api/classes/${classId}/export`, {
      params: { format },
      responseType: 'blob',
    })
    return response.data
  },

  downloadBlob(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  },
}

