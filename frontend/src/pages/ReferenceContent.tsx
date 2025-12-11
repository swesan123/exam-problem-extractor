import { useState, useEffect, useCallback } from 'react'
import { embedService } from '../services/embedService'
import { ocrService } from '../services/ocrService'
import { classService } from '../services/classService'
import { Class } from '../types/class'
import { EmbeddingRequest } from '../types/embedding'

interface FileWithStatus {
  file: File
  status: 'pending' | 'processing' | 'success' | 'error'
  progress?: number
  error?: string
  extractedText?: string
}

const ReferenceContent = () => {
  const [classes, setClasses] = useState<Class[]>([])
  const [selectedClassId, setSelectedClassId] = useState<string>('')
  const [examSource, setExamSource] = useState('')
  const [examType, setExamType] = useState('')
  const [files, setFiles] = useState<FileWithStatus[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    const loadClasses = async () => {
      try {
        const response = await classService.getAll()
        setClasses(response.classes || [])
      } catch (err) {
        console.error('Failed to load classes:', err)
        // Don't crash the page if classes fail to load
        setClasses([])
      }
    }
    loadClasses()
  }, [])

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
            // Create a File object from the blob with a name
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

  const processFile = async (fileWithStatus: FileWithStatus, index: number): Promise<string> => {
    // Update status to processing
    setFiles((prev) =>
      prev.map((f, i) => (i === index ? { ...f, status: 'processing', progress: 0 } : f))
    )

    try {
      let extractedText = ''

      if (fileWithStatus.file.type === 'application/pdf') {
        // For PDFs, use OCR service (backend now supports PDFs)
        setFiles((prev) =>
          prev.map((f, i) => (i === index ? { ...f, progress: 50 } : f))
        )

        const ocrResponse = await ocrService.extractText(fileWithStatus.file)
        extractedText = ocrResponse.text

        if (!extractedText || extractedText.trim().length === 0) {
          throw new Error('No text extracted from PDF')
        }
      } else {
        // For images, use OCR
        setFiles((prev) =>
          prev.map((f, i) => (i === index ? { ...f, progress: 50 } : f))
        )

        const ocrResponse = await ocrService.extractText(fileWithStatus.file)
        extractedText = ocrResponse.text

        if (!extractedText || extractedText.trim().length === 0) {
          throw new Error('No text extracted from image')
        }
      }

      // Update with extracted text
      setFiles((prev) =>
        prev.map((f, i) =>
          i === index ? { ...f, status: 'success', progress: 100, extractedText } : f
        )
      )

      return extractedText
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to process file'
      setFiles((prev) =>
        prev.map((f, i) =>
          i === index ? { ...f, status: 'error', error: errorMessage } : f
        )
      )
      throw err
    }
  }

  const embedText = async (text: string, fileName: string): Promise<void> => {
    const chunkId = `chunk_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    const request: EmbeddingRequest = {
      text: text.trim(),
      metadata: {
        source: examSource || fileName || 'uploaded_file',
        chunk_id: chunkId,
        page: undefined,
        exam_type: examType || undefined,
        class_id: selectedClassId || undefined,
      },
    }

    await embedService.embedText(request)
  }

  const handleProcessAll = async () => {
    if (files.length === 0) {
      setError('Please add at least one file')
      return
    }

    setProcessing(true)
    setError(null)
    setSuccess(null)

    const successful: string[] = []
    const failed: string[] = []

    try {
      // Process files sequentially to avoid overwhelming the API
      for (let i = 0; i < files.length; i++) {
        const fileWithStatus = files[i]

        if (fileWithStatus.status === 'success') {
          // Already processed, just embed
          if (fileWithStatus.extractedText) {
            try {
              await embedText(fileWithStatus.extractedText, fileWithStatus.file.name)
              successful.push(fileWithStatus.file.name)
            } catch (err) {
              failed.push(fileWithStatus.file.name)
            }
          }
        } else if (fileWithStatus.status !== 'error') {
          try {
            const extractedText = await processFile(fileWithStatus, i)
            await embedText(extractedText, fileWithStatus.file.name)
            successful.push(fileWithStatus.file.name)
          } catch (err) {
            failed.push(fileWithStatus.file.name)
          }
        } else {
          failed.push(fileWithStatus.file.name)
        }
      }

      if (successful.length > 0) {
        setSuccess(
          `Successfully processed ${successful.length} file(s): ${successful.join(', ')}`
        )
        // Reset form after successful processing
        setTimeout(() => {
          setFiles([])
          setExamSource('')
          setExamType('')
          setSelectedClassId('')
        }, 3000)
      }

      if (failed.length > 0) {
        setError(`Failed to process ${failed.length} file(s): ${failed.join(', ')}`)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process files')
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Add Reference Content</h1>

      <div className="bg-white rounded-lg shadow p-6 max-w-4xl">
        <p className="text-gray-600 mb-6">
          Drag and drop images or PDFs, click to select files, or paste images from your clipboard.
          The OCR functionality will parse and store them as reference material for question generation.
        </p>

        <div className="mb-6">
          <label htmlFor="class" className="block text-sm font-medium text-gray-700 mb-1">
            Class (Optional - to associate with a class)
          </label>
          <select
            id="class"
            value={selectedClassId}
            onChange={(e) => setSelectedClassId(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select a class...</option>
            {classes.map((classItem) => (
              <option key={classItem.id} value={classItem.id}>
                {classItem.name}
              </option>
            ))}
          </select>
        </div>

        <div className="mb-6 grid grid-cols-1 md:grid-cols-2 gap-4">
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
        </div>

        {/* Drag and Drop Zone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            isDragging
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 bg-gray-50 hover:border-gray-400'
          }`}
        >
          <input
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

        {/* File List */}
        {files.length > 0 && (
          <div className="mt-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">
              Files ({files.length})
            </h3>
            <div className="space-y-2">
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
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-800 text-sm">
            {error}
          </div>
        )}

        {success && (
          <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded text-green-800 text-sm">
            {success}
          </div>
        )}

        <button
          onClick={handleProcessAll}
          disabled={processing || files.length === 0}
          className="mt-6 w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {processing
            ? `Processing ${files.filter((f) => f.status === 'processing').length} file(s)...`
            : `Process and Store ${files.length} File(s)`}
        </button>
      </div>

      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-blue-900 mb-2">How it works:</h3>
        <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
          <li>Upload images or PDFs using drag and drop, file selection, or paste from clipboard</li>
          <li>OCR extracts text from each image/PDF automatically</li>
          <li>PDFs are processed page-by-page and all text is extracted</li>
          <li>Extracted text is embedded into the vector database</li>
          <li>When generating questions, similar content is retrieved automatically</li>
          <li>This helps generate questions in the same style and format</li>
        </ul>
      </div>
    </div>
  )
}

export default ReferenceContent
