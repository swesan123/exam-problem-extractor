import { useState, useRef, useEffect, useCallback } from 'react'
import { jobService } from '../services/jobService'

interface FileWithStatus {
  file: File
  status: 'pending' | 'processing' | 'success' | 'error'
  progress?: number
  error?: string
  extractedText?: string
}

interface AddReferenceContentModalProps {
  classId: string
  onClose: () => void
  onSuccess: () => void
}

const AddReferenceContentModal = ({
  classId,
  onClose,
  onSuccess,
}: AddReferenceContentModalProps) => {
  const [examSource, setExamSource] = useState('')
  const [examType, setExamType] = useState('')
  const [referenceType, setReferenceType] = useState('')
  const [files, setFiles] = useState<FileWithStatus[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const isValidFile = (file: File): boolean => {
    const validImageTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp']
    const validPdfType = 'application/pdf'
    return validImageTypes.includes(file.type) || file.type === validPdfType
  }

  const handleFiles = useCallback((fileList: FileList | File[]) => {
    const newFiles: FileWithStatus[] = []
    const filesArray = Array.from(fileList)

    filesArray.forEach((file) => {
      if (!isValidFile(file)) {
        setError(`Invalid file type: ${file.name}. Please upload images (PNG, JPG, JPEG) or PDFs.`)
        return
      }
      if (file.size > 10 * 1024 * 1024) {
        setError(`File too large: ${file.name}. Maximum size is 10MB.`)
        return
      }
      newFiles.push({
        file,
        status: 'pending',
      })
    })

    if (newFiles.length > 0) {
      setFiles((prev) => [...prev, ...newFiles])
      setError(null)
    }
  }, [])

  // Handle paste from clipboard
  useEffect(() => {
    const handlePaste = async (e: ClipboardEvent) => {
      const items = e.clipboardData?.items
      if (!items) return

      const imageFiles: File[] = []

      for (let i = 0; i < items.length; i++) {
        const item = items[i]
        if (item.type.indexOf('image') !== -1) {
          const blob = item.getAsFile()
          if (blob) {
            const file = new File([blob], `pasted-image-${Date.now()}.png`, {
              type: blob.type,
            })
            imageFiles.push(file)
          }
        }
      }

      if (imageFiles.length > 0) {
        e.preventDefault()
        handleFiles(imageFiles)
      }
    }

    window.addEventListener('paste', handlePaste)
    return () => {
      window.removeEventListener('paste', handlePaste)
    }
  }, [handleFiles])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragging(false)

      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files)
      }
    },
    [handleFiles]
  )

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFiles(e.target.files)
      }
    },
    [handleFiles]
  )

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const handleProcessAll = async () => {
    if (files.length === 0) {
      setError('Please add at least one file')
      return
    }

    setProcessing(true)
    setError(null)
    setSuccess(null)

    try {
      const fileList = files.map((f) => f.file)
      await jobService.uploadReferenceContent(
        classId,
        fileList,
        examSource || undefined,
        examType || undefined,
        referenceType || undefined
      )

      setSuccess('Upload started! Processing in background...')
      
      // Close modal immediately after job is created
      setTimeout(() => {
        onSuccess()
        onClose()
      }, 1000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload files')
      setProcessing(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-gray-900">Add Reference Content</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            disabled={processing}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="mb-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label htmlFor="exam_source" className="block text-sm font-medium text-gray-700 mb-1">
              Exam Source (Optional)
            </label>
            <input
              type="text"
              id="exam_source"
              value={examSource}
              onChange={(e) => setExamSource(e.target.value)}
              placeholder="e.g., '2023 Final Exam', 'Practice Test 1'"
              className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label htmlFor="exam_type" className="block text-sm font-medium text-gray-700 mb-1">
              Exam Type (Optional)
            </label>
            <select
              id="exam_type"
              value={examType}
              onChange={(e) => setExamType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select type...</option>
              <option value="practice_exam">Practice Exam</option>
              <option value="test">Test</option>
              <option value="quiz">Quiz</option>
              <option value="homework">Homework</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div>
            <label htmlFor="reference_type" className="block text-sm font-medium text-gray-700 mb-1">
              Reference Type (Optional)
            </label>
            <select
              id="reference_type"
              value={referenceType}
              onChange={(e) => setReferenceType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select type...</option>
              <option value="assessment">Assessment (structure/format)</option>
              <option value="lecture">Lecture (content/topics)</option>
              <option value="homework">Homework</option>
              <option value="notes">Notes</option>
              <option value="textbook">Textbook</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Assessment defines structure, Lecture defines content
            </p>
          </div>
        </div>

        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors mb-4 ${
            isDragging
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 bg-gray-50 hover:border-gray-400'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            id="file-input"
            multiple
            accept="image/*,.pdf"
            onChange={handleFileInput}
            className="hidden"
          />
          <label
            htmlFor="file-input"
            className="cursor-pointer flex flex-col items-center"
          >
            <svg
              className="w-12 h-12 text-gray-400 mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p className="text-gray-600 mb-2">
              <span className="text-blue-600 font-medium">Click to upload</span>, drag and drop, or{' '}
              <span className="text-blue-600 font-medium">paste from clipboard</span>
            </p>
            <p className="text-sm text-gray-500">
              Images (PNG, JPG, JPEG) or PDFs (max 10MB each)
            </p>
          </label>
        </div>

        {files.length > 0 && (
          <div className="mb-4">
            <h3 className="text-sm font-medium text-gray-700 mb-3">
              Files ({files.length})
            </h3>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {files.map((fileWithStatus, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200"
                >
                  <div className="flex items-center flex-1 min-w-0">
                    <div className="flex-shrink-0 mr-3">
                      {fileWithStatus.status === 'processing' && (
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                      )}
                      {fileWithStatus.status === 'success' && (
                        <svg
                          className="w-5 h-5 text-green-600"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M5 13l4 4L19 7"
                          />
                        </svg>
                      )}
                      {fileWithStatus.status === 'error' && (
                        <svg
                          className="w-5 h-5 text-red-600"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M6 18L18 6M6 6l12 12"
                          />
                        </svg>
                      )}
                      {fileWithStatus.status === 'pending' && (
                        <div className="w-5 h-5 border-2 border-gray-300 rounded"></div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {fileWithStatus.file.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {(fileWithStatus.file.size / 1024).toFixed(1)} KB
                        {fileWithStatus.progress !== undefined &&
                          fileWithStatus.progress > 0 &&
                          ` • ${fileWithStatus.progress}%`}
                      </p>
                      {fileWithStatus.error && (
                        <p className="text-xs text-red-600 mt-1">{fileWithStatus.error}</p>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => removeFile(index)}
                    className="ml-3 text-red-600 hover:text-red-800"
                    title="Remove file"
                  >
                    <svg
                      className="w-5 h-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-800 text-sm">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded text-green-800 text-sm">
            {success}
          </div>
        )}

        <div className="flex justify-end space-x-3">
          <button
            type="button"
            onClick={onClose}
            disabled={processing}
            className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleProcessAll}
            disabled={processing || files.length === 0}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {processing
              ? `Processing ${files.filter((f) => f.status === 'processing').length} file(s)...`
              : `Process and Store ${files.length} File(s)`}
          </button>
        </div>
      </div>
    </div>
  )
}

export default AddReferenceContentModal

