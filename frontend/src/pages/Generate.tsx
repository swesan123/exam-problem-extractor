import { useState, useRef, useEffect, useCallback } from 'react'
import { generateService, GenerateRequest } from '../services/generateService'
import { GenerateResponse } from '../types/question'
import { classService } from '../services/classService'
import { Class } from '../types/class'
import ClassesSidebar from '../components/ClassesSidebar'

interface FileWithStatus {
  file: File
  status: 'pending' | 'processing' | 'success' | 'error'
  error?: string
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  files?: FileWithStatus[]
  result?: GenerateResponse
  timestamp: Date
}

const Generate = () => {
  const [selectedClassId, setSelectedClassId] = useState<string>('')
  const [messages, setMessages] = useState<Message[]>([])
  const [textInput, setTextInput] = useState('')
  const [files, setFiles] = useState<FileWithStatus[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [includeSolution, setIncludeSolution] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [estimatedTime, setEstimatedTime] = useState<string | null>(null)
  const [showSettingsMenu, setShowSettingsMenu] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [selectedClassName, setSelectedClassName] = useState<string>('')
  const [classes, setClasses] = useState<Class[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const settingsMenuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    const loadClasses = async () => {
      try {
        const response = await classService.getAll()
        setClasses(response.classes || [])
      } catch (err) {
        console.error('Failed to load classes:', err)
      }
    }
    loadClasses()
  }, [])

  // Close settings menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (settingsMenuRef.current && !settingsMenuRef.current.contains(event.target as Node)) {
        setShowSettingsMenu(false)
      }
    }

    if (showSettingsMenu) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showSettingsMenu])

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

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()

    if (!textInput.trim() && files.length === 0) {
      setError('Please provide either text or upload an image/PDF')
      return
    }

    // Capture current values before clearing
    const currentTextInput = textInput.trim()
    const currentFiles = [...files]

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: currentTextInput || (currentFiles.length > 0 ? `Uploaded ${currentFiles.length} file(s)` : ''),
      files: currentFiles,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])

    // Clear text input and files immediately, but keep selected options (class and include solution)
    setTextInput('')
    setFiles([])
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    // Use the first file if multiple files are selected
    const imageFile = currentFiles.length > 0 ? currentFiles[0].file : null

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

    // Store assistant message ID for later
    const assistantMessageId = (Date.now() + 1).toString()

    try {
      const request: GenerateRequest = {
        include_solution: includeSolution,
        class_id: selectedClassId || undefined,
      }

      if (imageFile) {
        request.image_file = imageFile
        if (currentTextInput) {
          request.retrieved_context = currentTextInput
        }
      } else {
        request.ocr_text = currentTextInput || undefined
      }

      const response = await generateService.generate(request)

      // Add assistant message with result
      const assistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: response.question,
        result: response,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMessage])
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate question'
      setError(errorMessage)
      // Add assistant message with error
      const errorAssistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: `Error: ${errorMessage}`,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorAssistantMessage])
    } finally {
      setLoading(false)
      setEstimatedTime(null)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!loading) {
        handleSubmit()
      }
    }
  }

  return (
    <div className="flex h-screen w-full bg-white">
      {/* Sidebar */}
      <ClassesSidebar
        selectedClassId={selectedClassId}
        onSelectClass={(classId) => {
          setSelectedClassId(classId)
          if (!classId) {
            setSelectedClassName('')
          }
        }}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        onClassNameChange={setSelectedClassName}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col bg-white overflow-hidden h-screen">
      {messages.length === 0 ? (
        /* Centered layout when no messages and no text */
        <div className="flex-1 flex flex-col items-center justify-center px-4">
          <div className="flex flex-col items-center justify-center mb-8 text-center">
            <div className="mb-4">
              <svg
                className="w-16 h-16 text-gray-400 mx-auto"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-semibold text-gray-900 mb-2">How can I help you today?</h2>
            <p className="text-gray-500 mb-8">Upload an image/PDF or paste text to generate exam questions</p>
          </div>
          
          {/* Centered Input */}
          <div className="w-full max-w-3xl">
            {error && (
              <div className="mb-2 p-2 bg-red-50 border border-red-200 rounded text-red-800 text-xs">
                {error}
              </div>
            )}

            {/* File attachments */}
            {files.length > 0 && (
              <div className="mb-2 flex flex-wrap gap-2">
                {files.map((fileWithStatus, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-2 px-2 py-1 bg-gray-100 rounded text-xs text-gray-700"
                  >
                    <span>📎 {fileWithStatus.file.name}</span>
                    <button
                      type="button"
                      onClick={() => removeFile(index)}
                      className="text-red-600 hover:text-red-800"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}

            <form onSubmit={handleSubmit} className="relative">
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`relative rounded-3xl border transition-colors bg-white ${
                  isDragging
                    ? 'border-blue-500 shadow-lg'
                    : 'border-gray-300 shadow-md hover:shadow-lg'
                }`}
              >
                {/* Settings menu button */}
                <div className="absolute left-3 bottom-3" ref={settingsMenuRef}>
                  <button
                    type="button"
                    onClick={() => setShowSettingsMenu(!showSettingsMenu)}
                    className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition"
                    title="Add settings"
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
                        d="M12 4v16m8-8H4"
                      />
                    </svg>
                  </button>
                  
                  {/* Settings dropdown menu - opens downward when centered */}
                  {showSettingsMenu && (
                    <div className="absolute top-full left-0 mt-2 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-50 p-3 max-h-[80vh] overflow-y-auto">
                      <div className="mb-3">
                        <label className="block text-xs font-medium text-gray-700 mb-1.5">
                          Class
                        </label>
                        <select
                          value={selectedClassId}
                          onChange={(e) => {
                            const classId = e.target.value
                            setSelectedClassId(classId)
                            const selectedClass = classes.find(c => c.id === classId)
                            setSelectedClassName(selectedClass ? selectedClass.name : '')
                            setShowSettingsMenu(false)
                          }}
                          className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="">No class selected</option>
                          {classes.map((classItem) => (
                            <option key={classItem.id} value={classItem.id}>
                              {classItem.name}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="pt-2 border-t border-gray-200">
                        <label className="flex items-center text-sm text-gray-700 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={includeSolution}
                            onChange={(e) => {
                              setIncludeSolution(e.target.checked)
                              setShowSettingsMenu(false)
                            }}
                            className="mr-2 w-4 h-4 accent-blue-600 border-gray-300 rounded focus:ring-blue-500"
                          />
                          Include solution
                        </label>
                      </div>
                    </div>
                  )}
                </div>

                {/* Chips for selected options - shown inside textarea area */}
                {(selectedClassId || includeSolution) && (
                  <div className="flex items-center gap-2 pl-12 pr-20 pt-3.5 pb-1 flex-wrap">
                    {selectedClassId && selectedClassName && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
                        {selectedClassName}
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectedClassId('')
                            setSelectedClassName('')
                          }}
                          className="hover:bg-blue-200 rounded-full p-0.5 transition"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </span>
                    )}
                    {includeSolution && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
                        Include solution
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            setIncludeSolution(false)
                          }}
                          className="hover:bg-blue-200 rounded-full p-0.5 transition"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </span>
                    )}
                  </div>
                )}

                <textarea
                  ref={textareaRef}
                  value={textInput}
                  onChange={(e) => {
                    setTextInput(e.target.value)
                    e.target.style.height = 'auto'
                    e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`
                  }}
                  onKeyDown={handleKeyDown}
                  placeholder="Message Exam Problem Extractor..."
                  rows={1}
                  className={`w-full pl-12 pr-20 resize-none border-0 rounded-3xl focus:outline-none focus:ring-0 text-gray-900 placeholder-gray-500 bg-transparent text-base ${
                    selectedClassId || includeSolution ? 'pb-3.5' : 'py-3.5'
                  }`}
                  style={{ maxHeight: '200px' }}
                />
                <div className="absolute right-2 bottom-2 flex items-center gap-1">
                  <button
                    type="submit"
                    disabled={loading || (!textInput.trim() && files.length === 0)}
                    className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition disabled:bg-gray-300"
                    title="Send message"
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 7l5 5m0 0l-5 5m5-5H6"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      ) : (
        <>
          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto px-4 py-6">
            <div className="max-w-3xl mx-auto space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`max-w-[85%] ${
                    message.role === 'user' ? 'text-right' : 'text-left'
                  }`}
                >
                  {message.role === 'user' ? (
                    <div className="bg-gray-200 rounded-lg px-3 py-2 inline-block">
                      {message.files && message.files.length > 0 && (
                        <div className="mb-1 space-y-1">
                          {message.files.map((fileWithStatus, idx) => (
                            <div key={idx} className="text-sm text-gray-700">
                              📎 {fileWithStatus.file.name}
                            </div>
                          ))}
                        </div>
                      )}
                      {message.content && (
                        <div className="whitespace-pre-wrap text-sm leading-relaxed text-gray-900">
                          {message.content}
                        </div>
                      )}
                    </div>
                  ) : (
                    <>
                      {message.content && (
                        <div className="whitespace-pre-wrap text-sm leading-relaxed text-gray-900">
                          {message.content}
                        </div>
                      )}
                    </>
                  )}
                  {message.role === 'assistant' && message.result && (
                    <div className="mt-3 space-y-3">
                        {/* References and metadata */}
                        {message.result.references_used &&
                          (message.result.references_used.assessment?.length ||
                            message.result.references_used.lecture?.length) && (
                            <>
                              {/* Warning for low similarity scores */}
                              {(() => {
                                const minThreshold = 0.5
                                const allRefs = [
                                  ...(message.result.references_used.assessment || []),
                                  ...(message.result.references_used.lecture || []),
                                ]
                                const lowScoreRefs = allRefs.filter((ref) => ref.score < minThreshold)
                                const hasLowScores = lowScoreRefs.length > 0
                                const allLowScores =
                                  allRefs.length > 0 && allRefs.every((ref) => ref.score < minThreshold)

                                if (hasLowScores) {
                                  return (
                                    <div className="p-3 bg-yellow-50 border border-yellow-300 rounded-lg text-xs">
                                      <div className="flex items-start">
                                        <svg
                                          className="w-4 h-4 text-yellow-600 mr-2 flex-shrink-0 mt-0.5"
                                          fill="currentColor"
                                          viewBox="0 0 20 20"
                                        >
                                          <path
                                            fillRule="evenodd"
                                            d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                                            clipRule="evenodd"
                                          />
                                        </svg>
                                        <div>
                                          <p className="font-semibold text-yellow-900 mb-1">
                                            {allLowScores
                                              ? 'Warning: Low Reference Relevance'
                                              : 'Warning: Some References Have Low Relevance'}
                                          </p>
                                          <p className="text-yellow-800">
                                            {allLowScores
                                              ? 'The retrieved references have low similarity scores (below 0.5), indicating they may not be relevant to your question.'
                                              : 'Some retrieved references have low similarity scores (below 0.5) and were not used in generation.'}
                                          </p>
                                        </div>
                                      </div>
                                    </div>
                                  )
                                }
                                return null
                              })()}

                              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs">
                                <p className="font-semibold text-blue-900 mb-2">References Used:</p>
                                {message.result.references_used.assessment &&
                                  message.result.references_used.assessment.length > 0 && (
                                    <div className="mb-2">
                                      <p className="font-medium text-blue-800">Assessment:</p>
                                      <ul className="list-disc list-inside ml-2 text-blue-700">
                                        {message.result.references_used.assessment.map((ref, idx) => {
                                          const isLowScore = ref.score < 0.5
                                          return (
                                            <li key={idx} className={isLowScore ? 'text-yellow-700' : ''}>
                                              {ref.source_file} (score: {ref.score.toFixed(2)})
                                              {isLowScore && <span className="ml-1">⚠</span>}
                                            </li>
                                          )
                                        })}
                                      </ul>
                                    </div>
                                  )}
                                {message.result.references_used.lecture &&
                                  message.result.references_used.lecture.length > 0 && (
                                    <div>
                                      <p className="font-medium text-blue-800">Lecture:</p>
                                      <ul className="list-disc list-inside ml-2 text-blue-700">
                                        {message.result.references_used.lecture.map((ref, idx) => {
                                          const isLowScore = ref.score < 0.5
                                          return (
                                            <li key={idx} className={isLowScore ? 'text-yellow-700' : ''}>
                                              {ref.source_file} (score: {ref.score.toFixed(2)})
                                              {isLowScore && <span className="ml-1">⚠</span>}
                                            </li>
                                          )
                                        })}
                                      </ul>
                                    </div>
                                  )}
                              </div>
                            </>
                          )}

                        {message.result.question_id && (
                          <div className="p-2 bg-green-50 border border-green-200 rounded text-green-800 text-xs">
                            ✓ Question saved to class successfully!
                          </div>
                        )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="max-w-[85%] text-left">
                  <div className="flex items-center space-x-2">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                    {estimatedTime && (
                      <span className="text-xs text-gray-500 ml-2">{estimatedTime}</span>
                    )}
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input Area at bottom when there are messages or text */}
          <div className="border-t border-gray-200 bg-white px-4 py-4 pb-6">
        <div className="max-w-3xl mx-auto">
          {error && (
            <div className="mb-2 p-2 bg-red-50 border border-red-200 rounded text-red-800 text-xs">
              {error}
            </div>
          )}

          {/* File attachments */}
          {files.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-2">
              {files.map((fileWithStatus, index) => (
                <div
                  key={index}
                  className="flex items-center gap-2 px-2 py-1 bg-gray-100 rounded text-xs text-gray-700"
                >
                  <span>📎 {fileWithStatus.file.name}</span>
                  <button
                    type="button"
                    onClick={() => removeFile(index)}
                    className="text-red-600 hover:text-red-800"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}

          <form onSubmit={handleSubmit} className="relative">
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`relative rounded-3xl border transition-colors bg-white ${
                isDragging
                  ? 'border-blue-500 shadow-lg'
                  : 'border-gray-300 shadow-md hover:shadow-lg'
              }`}
            >
              {/* Settings menu button */}
              <div className="absolute left-3 bottom-3" ref={settingsMenuRef}>
                <button
                  type="button"
                  onClick={() => setShowSettingsMenu(!showSettingsMenu)}
                  className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition"
                  title="Add settings"
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
                      d="M12 4v16m8-8H4"
                    />
                  </svg>
                </button>
                
                {/* Settings dropdown menu - opens upward when at bottom */}
                {showSettingsMenu && (
                  <div className="absolute bottom-full left-0 mb-2 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-50 p-3 max-h-[80vh] overflow-y-auto">
                    <div className="mb-3">
                      <label className="block text-xs font-medium text-gray-700 mb-1.5">
                        Class
                      </label>
                      <select
                        value={selectedClassId}
                        onChange={(e) => {
                          const classId = e.target.value
                          setSelectedClassId(classId)
                          const selectedClass = classes.find(c => c.id === classId)
                          setSelectedClassName(selectedClass ? selectedClass.name : '')
                          setShowSettingsMenu(false)
                        }}
                        className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="">No class selected</option>
                        {classes.map((classItem) => (
                          <option key={classItem.id} value={classItem.id}>
                            {classItem.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="pt-2 border-t border-gray-200">
                      <label className="flex items-center text-sm text-gray-700 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={includeSolution}
                          onChange={(e) => {
                            setIncludeSolution(e.target.checked)
                            setShowSettingsMenu(false)
                          }}
                          className="mr-2 w-4 h-4 accent-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        />
                        Include solution
                      </label>
                    </div>
                  </div>
                )}
              </div>

              {/* Chips for selected options */}
              {(selectedClassId || includeSolution) && (
                <div className="flex items-center gap-2 pl-12 pr-20 pt-3.5 pb-1 flex-wrap">
                  {selectedClassId && selectedClassName && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
                      {selectedClassName}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedClassId('')
                          setSelectedClassName('')
                        }}
                        className="hover:bg-blue-200 rounded-full p-0.5 transition"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </span>
                  )}
                  {includeSolution && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
                      Include solution
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          setIncludeSolution(false)
                        }}
                        className="hover:bg-blue-200 rounded-full p-0.5 transition"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </span>
                  )}
                </div>
              )}

              <textarea
                ref={textareaRef}
                value={textInput}
                onChange={(e) => {
                  setTextInput(e.target.value)
                  e.target.style.height = 'auto'
                  e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`
                }}
                onKeyDown={handleKeyDown}
                placeholder="Message Exam Problem Extractor..."
                rows={1}
                className={`w-full pl-12 pr-20 resize-none border-0 rounded-3xl focus:outline-none focus:ring-0 text-gray-900 placeholder-gray-500 text-base ${
                  selectedClassId || includeSolution ? 'pb-3.5' : 'py-3.5'
                }`}
                style={{ maxHeight: '200px', background: 'transparent' }}
              />
              <div className="absolute right-2 bottom-2 flex items-center gap-1">
                <button
                  type="submit"
                  disabled={loading || (!textInput.trim() && files.length === 0)}
                  className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition disabled:bg-gray-300"
                  title="Send message"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 7l5 5m0 0l-5 5m5-5H6"
                    />
                  </svg>
                </button>
              </div>
            </div>
          </form>
        </div>
        </div>
        </>
      )}
      </div>
    </div>
  )
}

export default Generate
