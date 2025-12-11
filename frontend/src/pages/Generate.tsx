import { useState, useRef, useEffect, useCallback } from 'react'
import { generateService, GenerateRequest } from '../services/generateService'
import { classService } from '../services/classService'
import { Class } from '../types/class'
import { GenerateResponse } from '../types/question'

interface FileWithStatus {
  file: File
  status: 'pending' | 'processing' | 'success' | 'error'
  error?: string
}

const Generate = () => {
  const [classes, setClasses] = useState<Class[]>([])
  const [selectedClassId, setSelectedClassId] = useState<string>('')
  const [textInput, setTextInput] = useState('')
  const [files, setFiles] = useState<FileWithStatus[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [includeSolution, setIncludeSolution] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<GenerateResponse | null>(null)
  const [estimatedTime, setEstimatedTime] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const loadClasses = async () => {
      try {
        const response = await classService.getAll()
        setClasses(response.classes || [])
      } catch (err) {
        console.error('Failed to load classes:', err)
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!textInput && files.length === 0) {
      setError('Please provide either OCR text or upload an image/PDF')
      return
    }

    // Use the first file if multiple files are selected
    const imageFile = files.length > 0 ? files[0].file : null

    // Simple ETA heuristic based on file size/count
    const estimateSeconds = () => {
      if (imageFile) {
        const sizeMb = imageFile.size / (1024 * 1024)
        return Math.max(8, Math.round(6 + sizeMb * 3))
      }
      return 5
    }
    const etaSeconds = estimateSeconds()
    setEstimatedTime(`~${etaSeconds} sec`)

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const request: GenerateRequest = {
        include_solution: includeSolution,
        class_id: selectedClassId || undefined,
      }

      if (imageFile) {
        request.image_file = imageFile
        if (textInput) {
          request.retrieved_context = textInput
        }
      } else {
        request.ocr_text = textInput || undefined
      }

      const response = await generateService.generate(request)
      setResult(response)

      // Reset form if question was saved to class
      if (response.question_id) {
        setTextInput('')
        setFiles([])
        if (fileInputRef.current) {
          fileInputRef.current.value = ''
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate question')
    } finally {
      setLoading(false)
    }
  }

  const hasFiles = files.length > 0
  const textareaLabel = hasFiles ? 'Context for Images/PDFs (Optional)' : 'Enter OCR text'
  const textareaPlaceholder = hasFiles
    ? 'Add context about the images/PDFs to help generate better questions...'
    : 'Paste extracted text here...'

  return (
    <div className="px-4 py-6 sm:px-0">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Generate Question</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Input</h2>

          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label htmlFor="class" className="block text-sm font-medium text-gray-700 mb-1">
                Class (Optional - to save question)
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

            {/* Drag and Drop Zone */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Upload Image or PDF
              </label>
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
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

                {/* File List (inline in dropzone) */}
                {files.length > 0 && (
                  <div className="mt-4 space-y-2 text-left">
                    {files.map((fileWithStatus, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between p-2 bg-white rounded border border-gray-200"
                      >
                        <div className="flex items-center flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {fileWithStatus.file.name}
                          </p>
                          <span className="ml-2 text-xs text-gray-500">
                            ({(fileWithStatus.file.size / 1024).toFixed(1)} KB)
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => removeFile(index)}
                          className="ml-2 text-red-600 hover:text-red-800"
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
                    {files.length > 1 && (
                      <p className="text-xs text-gray-500 mt-1">
                        Note: Only the first file will be used for generation
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="mb-4">
              <label htmlFor="text_input" className="block text-sm font-medium text-gray-700 mb-1">
                {textareaLabel}
              </label>
              <textarea
                id="text_input"
                rows={6}
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder={textareaPlaceholder}
                className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="mb-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={includeSolution}
                  onChange={(e) => setIncludeSolution(e.target.checked)}
                  className="mr-2 w-4 h-4 text-blue-600 bg-white border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Include solution</span>
              </label>
            </div>

            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-800 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || (!textInput && files.length === 0)}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading
                ? `Generating...${estimatedTime ? ` (${estimatedTime})` : ''}`
                : 'Generate Question'}
            </button>
            {estimatedTime && !loading && (
              <p className="mt-2 text-xs text-gray-500">Estimated time: {estimatedTime}</p>
            )}
          </form>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Generated Question</h2>

          {result ? (
            <div>
              <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                <pre className="whitespace-pre-wrap text-sm text-gray-900">
                  {result.question}
                </pre>
              </div>

              {result.question_id && (
                <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded text-green-800 text-sm">
                  ✓ Question saved to class successfully!
                </div>
              )}

              <div className="text-xs text-gray-600">
                <p>Processing steps: {result.processing_steps.join(', ')}</p>
                {result.metadata && Object.keys(result.metadata).length > 0 && (
                  <details className="mt-2">
                    <summary className="cursor-pointer">View metadata</summary>
                    <pre className="mt-2 text-xs bg-gray-50 p-2 rounded overflow-auto">
                      {JSON.stringify(result.metadata, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            </div>
          ) : (
            <div className="text-gray-500 text-center py-12">
              Generated question will appear here
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Generate
