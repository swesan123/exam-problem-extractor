import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom'
import { classService } from '../services/classService'
import { referenceContentService, ReferenceContentItem } from '../services/referenceContentService'
import { Class } from '../types/class'
import { jobService } from '../services/jobService'

interface FileWithStatus {
  file: File
  status: 'pending' | 'processing' | 'success' | 'error'
  progress?: number
  error?: string
  extractedText?: string
}

const ClassDetails = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const returnTo = (location.state as { returnTo?: string })?.returnTo || '/classes'
  const [classItem, setClassItem] = useState<Class | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [referenceContent, setReferenceContent] = useState<ReferenceContentItem[]>([])
  const [loadingRefContent, setLoadingRefContent] = useState(false)
  const [deletingChunkId, setDeletingChunkId] = useState<string | null>(null)
  const [viewingFile, setViewingFile] = useState<string | null>(null)
  
  // Upload form state
  const [name, setName] = useState('')
  const [referenceType, setReferenceType] = useState('')
  const [files, setFiles] = useState<FileWithStatus[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [processingFileCount, setProcessingFileCount] = useState(0)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null)
  const [estimatedTime, setEstimatedTime] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  // Exam format editor state
  const [examFormat, setExamFormat] = useState('')
  const [isEditingExamFormat, setIsEditingExamFormat] = useState(false)
  const [savingExamFormat, setSavingExamFormat] = useState(false)

  useEffect(() => {
    const loadReferenceContent = async () => {
      if (!id) return

      try {
        setLoadingRefContent(true)
        const response = await referenceContentService.getByClass(id)
        setReferenceContent(response.items)
      } catch (err) {
        // Silently handle error - reference content is optional
        setReferenceContent([])
      } finally {
        setLoadingRefContent(false)
      }
    }

    const loadClass = async () => {
      if (!id) return

      try {
        setLoading(true)
        setError(null)
        const data = await classService.getById(id)
        setClassItem(data)
        setExamFormat(data.exam_format || '')
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load class')
      } finally {
        setLoading(false)
      }
    }

    loadClass()
    loadReferenceContent()
  }, [id])

  const handleDeleteReferenceContent = async (filename: string, chunks: ReferenceContentItem[]) => {
    if (!confirm(`Are you sure you want to delete all content from "${filename}"?`)) return

    try {
      setDeletingChunkId(filename)
      // Delete all chunks for this file
      await Promise.all(chunks.map(chunk => referenceContentService.delete(chunk.chunk_id)))
      // Reload reference content
      if (id) {
        const response = await referenceContentService.getByClass(id)
        setReferenceContent(response.items)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete reference content')
    } finally {
      setDeletingChunkId(null)
    }
  }

  const handleAddSuccess = async () => {
    if (!id) return
    try {
      setLoadingRefContent(true)
      const response = await referenceContentService.getByClass(id)
      setReferenceContent(response.items)
    } catch (err) {
      // Silently handle error
      setReferenceContent([])
    } finally {
      setLoadingRefContent(false)
    }
  }

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
        setUploadError(`Invalid file type: ${file.name}. Please upload images (PNG, JPG, JPEG) or PDFs.`)
        return
      }
      if (file.size > 10 * 1024 * 1024) {
        setUploadError(`File too large: ${file.name}. Maximum size is 10MB.`)
        return
      }
      newFiles.push({
        file,
        status: 'pending',
      })
    })

    if (newFiles.length > 0) {
      setFiles((prev) => [...prev, ...newFiles])
      setUploadError(null)
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
    if (!id) return
    if (files.length === 0) {
      setUploadError('Please add at least one file')
      return
    }

    // Calculate estimated time based on file sizes
    const estimateSeconds = () => {
      if (files.length === 0) return 5
      const totalSizeMb = files.reduce((sum, f) => sum + f.file.size / (1024 * 1024), 0)
      const avgSizeMb = totalSizeMb / files.length
      // Base time per file + size-based time
      return Math.max(10, Math.round(files.length * (6 + avgSizeMb * 3)))
    }
    const etaSeconds = estimateSeconds()
    setEstimatedTime(`~${etaSeconds} sec`)
    setProcessingFileCount(files.length)

    setProcessing(true)
    setUploadError(null)
    setUploadSuccess(null)

    try {
      const fileList = files.map((f) => f.file)
      await jobService.uploadReferenceContent(
        id,
        fileList,
        name || undefined,
        undefined, // examType removed
        referenceType || undefined
      )

      setUploadSuccess('Upload started! Processing in background...')
      
      // Reset form (but keep estimatedTime and processing state for now)
      setName('')
      setReferenceType('')
      setFiles([])
      
      // Reload reference content after a short delay
      setTimeout(() => {
        handleAddSuccess()
        // Keep processing state and estimate visible for a bit longer
        // since actual processing happens in background
        setTimeout(() => {
          setProcessing(false)
          setEstimatedTime(null)
          setProcessingFileCount(0)
        }, 3000) // Clear after 3 more seconds to show estimate
      }, 1000)
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Failed to upload files')
      setProcessing(false)
      setEstimatedTime(null)
      setProcessingFileCount(0)
    }
  }

  const handleSaveExamFormat = async () => {
    if (!id) return
    
    try {
      setSavingExamFormat(true)
      const updated = await classService.updateExamFormat(id, examFormat)
      setClassItem(updated)
      setIsEditingExamFormat(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save exam format')
    } finally {
      setSavingExamFormat(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-600">Loading class details...</div>
      </div>
    )
  }

  if (error || !classItem) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">Error: {error || 'Class not found'}</p>
        <button
          onClick={() => navigate(returnTo)}
          className="mt-2 inline-block text-blue-600 hover:text-blue-800"
        >
          Back
        </button>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <div className="px-4 py-6 sm:px-0 flex-1 overflow-y-auto">
      <button
        onClick={() => navigate(returnTo)}
        className="text-blue-600 hover:text-blue-800 mb-4 inline-block"
      >
        ← Back
      </button>

      <div className="bg-white rounded-lg shadow p-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">{classItem.name}</h1>

        {classItem.subject && (
          <div className="mb-4">
            <span className="text-sm font-medium text-gray-700">Subject:</span>
            <span className="ml-2 text-gray-900">{classItem.subject}</span>
          </div>
        )}

        {classItem.description && (
          <div className="mb-4">
            <span className="text-sm font-medium text-gray-700">Description:</span>
            <p className="mt-1 text-gray-900">{classItem.description}</p>
          </div>
        )}

        {/* Exam Format Section */}
        <div className="mb-6 pt-6 border-t border-gray-200">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Exam Format</h2>
            {!isEditingExamFormat && (
              <button
                onClick={() => setIsEditingExamFormat(true)}
                className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition"
              >
                {classItem.exam_format ? 'Edit' : 'Set Exam Format'}
              </button>
            )}
          </div>

          {isEditingExamFormat ? (
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <label htmlFor="exam_format" className="block text-sm font-medium text-gray-700 mb-2">
                Exam Format Template
              </label>
              <textarea
                id="exam_format"
                value={examFormat}
                onChange={(e) => setExamFormat(e.target.value)}
                placeholder="e.g., '5 multiple choice questions, 3 short answer questions, 2 long answer questions'"
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-500 mt-2">
                Example: "10 questions total: 6 multiple choice (2 points each), 4 short answer (5 points each)"
              </p>
              <div className="flex justify-end gap-2 mt-4">
                <button
                  onClick={() => {
                    setIsEditingExamFormat(false)
                    setExamFormat(classItem.exam_format || '')
                  }}
                  className="px-4 py-2 text-sm border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                  disabled={savingExamFormat}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveExamFormat}
                  disabled={savingExamFormat}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {savingExamFormat ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              {classItem.exam_format ? (
                <p className="text-gray-900">{classItem.exam_format}</p>
              ) : (
                <p className="text-gray-500 italic">No exam format set. Click "Set Exam Format" to add one.</p>
              )}
            </div>
          )}
        </div>
        {/* Reference Content Section */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Reference Content ({referenceContent.length})
          </h2>

          {/* Upload Form */}
          <div className="mb-6 bg-gray-50 rounded-lg p-6 border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Add Reference Content</h3>
            
            <div className="mb-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., '2023 Final Exam', 'Practice Test 1'"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label htmlFor="reference_type" className="block text-sm font-medium text-gray-700 mb-1">
                  Reference Type
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
                  : 'border-gray-300 bg-white hover:border-gray-400'
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
                <h4 className="text-sm font-medium text-gray-700 mb-3">
                  Files ({files.length})
                </h4>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {files.map((fileWithStatus, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-200"
                    >
                      <div className="flex items-center flex-1 min-w-0">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {fileWithStatus.file.name}
                          </p>
                          <p className="text-xs text-gray-500">
                            {(fileWithStatus.file.size / 1024).toFixed(1)} KB
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

            {uploadError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-800 text-sm">
                {uploadError}
              </div>
            )}

            {uploadSuccess && (
              <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded text-green-800 text-sm">
                {uploadSuccess}
              </div>
            )}

            <div className="flex justify-end">
              <button
                onClick={handleProcessAll}
                disabled={processing || files.length === 0}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {processing
                  ? `Processing ${processingFileCount} file(s)...${estimatedTime ? ` (${estimatedTime})` : ''}`
                  : `Process and Store ${files.length} File(s)`}
              </button>
            </div>
            {estimatedTime && !processing && (
              <p className="mt-2 text-xs text-gray-500 text-right">Estimated time: {estimatedTime}</p>
            )}
          </div>

          {/* Reference Content List */}
          {loadingRefContent ? (
            <div className="text-center py-4 text-gray-600">Loading reference content...</div>
          ) : referenceContent.length === 0 ? (
            <div className="text-center py-8 bg-gray-50 rounded-lg">
              <p className="text-gray-600">No reference content yet.</p>
            </div>
          ) : (() => {
            // Group chunks by filename (source_file or original_filename)
            const groupedByFile = referenceContent.reduce((acc, item) => {
              const filename = item.metadata.original_filename || item.metadata.source_file || item.metadata.source || 'Unknown File'
              if (!acc[filename]) {
                acc[filename] = []
              }
              acc[filename].push(item)
              return acc
            }, {} as Record<string, ReferenceContentItem[]>)

            // Also group by exam_source if available to show user-provided names
            const groupedBySource = referenceContent.reduce((acc, item) => {
              const sourceName = item.metadata.exam_source
              const filename = item.metadata.original_filename || item.metadata.source_file || item.metadata.source || 'Unknown File'
              // Use exam_source as key if available, otherwise use filename
              const key = sourceName || filename
              if (!acc[key]) {
                acc[key] = {
                  items: [],
                  displayName: sourceName || filename,
                  filename: filename,
                  referenceType: item.metadata.reference_type
                }
              }
              acc[key].items.push(item)
              return acc
            }, {} as Record<string, { items: ReferenceContentItem[], displayName: string, filename: string, referenceType?: string }>)

            return (
              <div className="space-y-3 max-h-96 overflow-y-auto custom-scrollbar">
                {Object.entries(groupedBySource).map(([key, group]) => {
                  const chunks = group.items
                  const displayName = group.displayName
                  const filename = group.filename
                  const referenceType = group.referenceType
                  
                  return (
                    <div
                      key={key}
                      className="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:shadow-md transition"
                    >
                      <div className="flex justify-between items-center">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-3 mb-1">
                            <span className="text-sm font-medium text-gray-900 truncate">
                              {displayName}
                            </span>
                            {referenceType && (
                              <span className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded whitespace-nowrap">
                                {referenceType}
                              </span>
                            )}
                            <span className="text-xs text-gray-500 whitespace-nowrap">
                              {chunks.length} chunk{chunks.length !== 1 ? 's' : ''}
                            </span>
                          </div>
                          {displayName !== filename && (
                            <p className="text-xs text-gray-400 mt-0.5 truncate">
                              {filename}
                            </p>
                          )}
                          {chunks[0]?.metadata.timestamp && (
                            <p className="text-xs text-gray-500 mt-1">
                              Added: {new Date(chunks[0].metadata.timestamp).toLocaleDateString()}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center space-x-2 ml-4">
                          <button
                            onClick={() => setViewingFile(viewingFile === key ? null : key)}
                            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition"
                          >
                            {viewingFile === key ? 'Hide' : 'View'} Content
                          </button>
                          <button
                            onClick={() => handleDeleteReferenceContent(filename, chunks)}
                            disabled={deletingChunkId === filename}
                            className="p-1.5 text-red-600 hover:text-red-800 disabled:opacity-50"
                            title="Delete file"
                          >
                            {deletingChunkId === filename ? (
                              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-red-600"></div>
                            ) : (
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
                                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                                />
                              </svg>
                            )}
                          </button>
                        </div>
                      </div>
                      {viewingFile === key && (
                        <div className="mt-4 pt-4 border-t border-gray-200">
                          <div className="space-y-3 max-h-96 overflow-y-auto">
                            {chunks.map((chunk, idx) => {
                              const isEditing = editingChunkId === chunk.chunk_id
                              const isUpdating = updatingChunk === chunk.chunk_id
                              const effectiveMetadata = chunk.metadata
                              const examRegion = effectiveMetadata?.exam_region as 'pre' | 'post' | undefined
                              const slideset = effectiveMetadata?.slideset as string | undefined
                              const slideNumber = effectiveMetadata?.slide_number as number | undefined
                              const topic = effectiveMetadata?.topic as string | undefined
                              const autoTags = effectiveMetadata?.auto_tags as Record<string, any> | undefined
                              const userOverrides = effectiveMetadata?.user_overrides as Record<string, any> | undefined
                              const hasUserOverrides = userOverrides && Object.keys(userOverrides).length > 0

                              const handleSaveChunkTags = async () => {
                                try {
                                  setUpdatingChunk(chunk.chunk_id)
                                  await referenceContentService.update(chunk.chunk_id, {
                                    exam_region: chunkTagForm.exam_region === null ? null : chunkTagForm.exam_region,
                                    slideset: chunkTagForm.slideset || undefined,
                                    slide_number: chunkTagForm.slide_number ? parseInt(chunkTagForm.slide_number) : undefined,
                                    topic: chunkTagForm.topic || undefined,
                                  })
                                  setEditingChunkId(null)
                                  // Reload reference content
                                  if (id) {
                                    const response = await referenceContentService.getByClass(id)
                                    setReferenceContent(response.items)
                                  }
                                } catch (err) {
                                  console.error('Failed to update chunk tags:', err)
                                } finally {
                                  setUpdatingChunk(null)
                                }
                              }

                              const handleStartEdit = () => {
                                setChunkTagForm({
                                  exam_region: examRegion || null,
                                  slideset: slideset || '',
                                  slide_number: slideNumber?.toString() || '',
                                  topic: topic || '',
                                })
                                setEditingChunkId(chunk.chunk_id)
                              }

                              const handleCancelEdit = () => {
                                setEditingChunkId(null)
                                setChunkTagForm({})
                              }

                              return (
                                <div key={chunk.chunk_id} className="bg-white rounded p-3 border border-gray-200">
                                  <div className="flex items-start justify-between mb-2">
                                    <div className="text-xs text-gray-500">Chunk {idx + 1}</div>
                                    {!isEditing && (
                                      <button
                                        onClick={handleStartEdit}
                                        className="text-xs text-blue-600 hover:text-blue-800"
                                      >
                                        Tag
                                      </button>
                                    )}
                                  </div>
                                  <p className="text-sm text-gray-700 whitespace-pre-wrap mb-3">{chunk.text}</p>
                                  
                                  {/* Tags display */}
                                  {(examRegion || slideset || slideNumber || topic || autoTags || userOverrides) && !isEditing && (
                                    <div className="mt-3 pt-3 border-t border-gray-200">
                                      {hasUserOverrides && (
                                        <div className="mb-2 text-xs text-orange-600 font-medium">
                                          ⚠ User overrides applied
                                        </div>
                                      )}
                                      <div className="flex flex-wrap gap-2 text-xs">
                                        {examRegion && (
                                          <span className={`px-2 py-1 rounded ${
                                            examRegion === 'pre' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'
                                          }`}>
                                            {examRegion === 'pre' ? 'Pre-midterm' : 'Post-midterm'}
                                          </span>
                                        )}
                                        {slideset && (
                                          <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded">
                                            Slideset: {slideset}
                                          </span>
                                        )}
                                        {slideNumber !== undefined && (
                                          <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded">
                                            Slide: {slideNumber}
                                          </span>
                                        )}
                                        {topic && (
                                          <span className="px-2 py-1 bg-indigo-100 text-indigo-700 rounded">
                                            Topic: {topic}
                                          </span>
                                        )}
                                      </div>
                                      {autoTags && Object.keys(autoTags).length > 0 && (
                                        <div className="mt-2 text-xs text-gray-500">
                                          Auto-tags: {JSON.stringify(autoTags)}
                                        </div>
                                      )}
                                    </div>
                                  )}

                                  {/* Tag editing form */}
                                  {isEditing && (
                                    <div className="mt-3 pt-3 border-t border-gray-200 space-y-3">
                                      <div>
                                        <label className="block text-xs text-gray-600 mb-1">Exam Region</label>
                                        <select
                                          value={chunkTagForm.exam_region || ''}
                                          onChange={(e) => setChunkTagForm({
                                            ...chunkTagForm,
                                            exam_region: e.target.value === '' ? null : e.target.value as 'pre' | 'post'
                                          })}
                                          className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        >
                                          <option value="">Not specified</option>
                                          <option value="pre">Pre-midterm</option>
                                          <option value="post">Post-midterm</option>
                                        </select>
                                      </div>
                                      <div>
                                        <label className="block text-xs text-gray-600 mb-1">Slideset</label>
                                        <input
                                          type="text"
                                          value={chunkTagForm.slideset || ''}
                                          onChange={(e) => setChunkTagForm({ ...chunkTagForm, slideset: e.target.value })}
                                          className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                          placeholder="e.g., Lecture_5"
                                        />
                                      </div>
                                      <div>
                                        <label className="block text-xs text-gray-600 mb-1">Slide Number</label>
                                        <input
                                          type="number"
                                          min="1"
                                          value={chunkTagForm.slide_number || ''}
                                          onChange={(e) => setChunkTagForm({ ...chunkTagForm, slide_number: e.target.value })}
                                          className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                          placeholder="e.g., 12"
                                        />
                                      </div>
                                      <div>
                                        <label className="block text-xs text-gray-600 mb-1">Topic</label>
                                        <input
                                          type="text"
                                          value={chunkTagForm.topic || ''}
                                          onChange={(e) => setChunkTagForm({ ...chunkTagForm, topic: e.target.value })}
                                          className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                          placeholder="e.g., Linear Algebra"
                                        />
                                      </div>
                                      <div className="flex gap-2">
                                        <button
                                          onClick={handleSaveChunkTags}
                                          disabled={isUpdating}
                                          className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition disabled:opacity-50"
                                        >
                                          {isUpdating ? 'Saving...' : 'Save'}
                                        </button>
                                        <button
                                          onClick={handleCancelEdit}
                                          disabled={isUpdating}
                                          className="px-3 py-1.5 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition disabled:opacity-50"
                                        >
                                          Cancel
                                        </button>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )
          })()}
        </div>
      </div>
      </div>
    </div>
  )
}

export default ClassDetails

