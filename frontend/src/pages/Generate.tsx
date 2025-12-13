import { useState, useRef, useEffect, useCallback } from 'react'
import { generateService, GenerateRequest } from '../services/generateService'
import { GenerateResponse } from '../types/question'
import { classService } from '../services/classService'
import { Class } from '../types/class'
import ClassesSidebar from '../components/ClassesSidebar'
import LatexRenderer from '../components/LatexRenderer'

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
  isMaxCoverageSummary?: boolean
  showPreview?: boolean
  timestamp: Date
}

const Generate = () => {
  const [selectedClassId, setSelectedClassId] = useState<string>('')
  const [messages, setMessages] = useState<Message[]>([])
  const [textInput, setTextInput] = useState('')
  const [files, setFiles] = useState<FileWithStatus[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [includeSolution, setIncludeSolution] = useState(false)
  const [maxCoverage, setMaxCoverage] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showSettingsMenu, setShowSettingsMenu] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [selectedClassName, setSelectedClassName] = useState<string>('')
  const [classes, setClasses] = useState<Class[]>([])
  const [mode, setMode] = useState<'normal' | 'mock_exam'>('normal')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const settingsMenuRef = useRef<HTMLDivElement>(null)
  const settingsButtonRef = useRef<HTMLButtonElement>(null)
  const [dropdownPosition, setDropdownPosition] = useState<'top' | 'bottom'>('bottom')

  useEffect(() => {
    // Scroll to bottom of messages area when new messages are added
    // Use setTimeout to ensure DOM is updated
    const timer = setTimeout(() => {
      if (messagesEndRef.current) {
        const messagesContainer = messagesEndRef.current.parentElement?.parentElement
        if (messagesContainer && messagesContainer.scrollHeight > messagesContainer.clientHeight) {
          // Only scroll if content overflows
          messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' })
        }
      }
    }, 100)
    return () => clearTimeout(timer)
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

  // Calculate dropdown position based on available space
  useEffect(() => {
    if (showSettingsMenu && settingsButtonRef.current) {
      // Use setTimeout to ensure dropdown is rendered before calculating
      const timer = setTimeout(() => {
        if (settingsButtonRef.current) {
          const buttonRect = settingsButtonRef.current.getBoundingClientRect()
          const viewportHeight = window.innerHeight
          const spaceBelow = viewportHeight - buttonRect.bottom
          const spaceAbove = buttonRect.top
          
          // Estimate dropdown height (approximately 250px for normal, 280px for mock_exam)
          const estimatedHeight = mode === 'mock_exam' ? 280 : 250
          
          // If not enough space below but enough above, open upward
          // Add some padding (20px) to ensure it doesn't touch edges
          if (spaceBelow < estimatedHeight + 20 && spaceAbove > estimatedHeight + 20) {
            setDropdownPosition('top')
          } else {
            setDropdownPosition('bottom')
          }
        }
      }, 0)
      
      return () => clearTimeout(timer)
    }
  }, [showSettingsMenu, mode])

  // Close settings menu when clicking outside (but not when clicking inside the dropdown or button)
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node
      // Check if click is outside both the dropdown menu and the button
      const isClickInMenu = settingsMenuRef.current?.contains(target)
      const isClickInButton = settingsButtonRef.current?.contains(target)
      
      if (!isClickInMenu && !isClickInButton) {
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

    // For normal mode, require input. For mock_exam, class_id is required but input is optional
    if (mode === 'normal' && !textInput.trim() && files.length === 0) {
      setError('Please provide either text or upload an image/PDF')
      return
    }
    
    if (mode === 'mock_exam' && !selectedClassId) {
      setError('Please select a class for mock exam mode')
      return
    }

    // Capture current values before clearing
    const currentTextInput = textInput.trim()
    const currentFiles = [...files]

    // Add user message
    // For mock exam mode, allow empty content
    const userMessageContent = currentTextInput || (currentFiles.length > 0 ? `Uploaded ${currentFiles.length} file(s)` : (mode === 'mock_exam' ? 'Generating mock exam...' : ''))
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: userMessageContent,
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
    setLoading(true)
    setError(null)

    // Store assistant message ID for later
    const assistantMessageId = (Date.now() + 1).toString()

    try {
      const request: GenerateRequest = {
        include_solution: includeSolution,
        class_id: selectedClassId || undefined,
        mode: mode,
        exam_format: mode === 'mock_exam' ? (classes.find(c => c.id === selectedClassId)?.exam_format || undefined) : undefined,
        max_coverage: mode === 'mock_exam' ? maxCoverage : undefined,
        question_count: mode === 'mock_exam' && questionCount !== 'auto' 
          ? (questionCount === 'custom' ? customQuestionCount : questionCount as number)
          : undefined,
        weighting_rules: mode === 'mock_exam' && weightingMode === 'custom'
          ? JSON.stringify({
              pre_midterm_weight: preMidtermWeight,
              post_midterm_weight: postMidtermWeight,
            })
          : undefined,
        focus_on_uncertain: mode === 'mock_exam' ? focusOnUncertain : undefined,
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

      // Handle both single question and batch questions
      let content = ''
      let isMaxCoverageSummary = false
      
      if (response.questions && response.questions.length > 0) {
        // Check if this is max coverage mode (multiple exams)
        const isMaxCoverage = maxCoverage && response.questions.length > 1
        const coverageMetric = response.metadata?.final_coverage || response.metadata?.coverage_metric
        
        if (isMaxCoverage) {
          // Show summary for max coverage instead of full content
          const coveragePercent = coverageMetric ? (typeof coverageMetric === 'number' ? (coverageMetric * 100).toFixed(1) : coverageMetric) : 'N/A'
          content = `✅ **${response.questions.length} mock exam(s) generated successfully**\n\n**Coverage:** ${coveragePercent}%\n\nClick "Preview Exams" below to view the generated exams.`
          isMaxCoverageSummary = true
        } else {
          // Single mock exam - show full content
          content = response.questions[0]
        }
      } else if (response.question) {
        content = response.question
      }

      // Add assistant message with result
      const assistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: content,
        result: response,
        isMaxCoverageSummary: isMaxCoverageSummary,
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
    <div className="flex h-screen w-full bg-white" style={{ backgroundColor: 'white', height: '100vh', maxHeight: '100vh', overflow: 'hidden' }}>
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
      <div className="flex-1 flex flex-col bg-white overflow-hidden" style={{ backgroundColor: 'white', height: '100vh', maxHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {messages.length === 0 ? (
        /* Centered layout when no messages and no text */
        <div className="flex-1 flex flex-col items-center justify-center px-4 bg-white" style={{ backgroundColor: 'white' }}>
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
                <div className="absolute left-3 bottom-3">
                  <button
                    ref={settingsButtonRef}
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
                  
                  {/* Settings dropdown menu - position dynamically based on available space */}
                  {showSettingsMenu && (() => {
                    const buttonRect = settingsButtonRef.current?.getBoundingClientRect()
                    const calculatedMaxHeight = dropdownPosition === 'top' 
                      ? (buttonRect ? Math.min(window.innerHeight * 0.8, buttonRect.top - 20) : 400)
                      : (buttonRect ? Math.min(window.innerHeight * 0.8, window.innerHeight - buttonRect.bottom - 20) : 400)
                    return (
                      <div 
                        ref={settingsMenuRef}
                        className={`absolute ${dropdownPosition === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'} left-0 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-50 p-3 overflow-y-auto`}
                        style={{
                          maxHeight: `${Math.max(calculatedMaxHeight, 200)}px` // Ensure minimum 200px
                        }}
                      >
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
                      <div className="mb-3 pt-2 border-t border-gray-200">
                        <label className="block text-xs font-medium text-gray-700 mb-1.5">
                          Generation Mode
                        </label>
                        <select
                          value={mode}
                          onChange={(e) => {
                            setMode(e.target.value as 'normal' | 'mock_exam')
                          }}
                          className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="normal">Normal</option>
                          <option value="mock_exam" disabled={!selectedClassId}>Mock Exam</option>
                        </select>
                        {mode === 'mock_exam' && !selectedClassId && (
                          <p className="mt-1 text-xs text-gray-500">Select a class to use mock exam mode</p>
                        )}
                      </div>
                      <div className="pt-2 border-t border-gray-200 space-y-2">
                        <button
                          type="button"
                          onClick={() => setIncludeSolution(!includeSolution)}
                          className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                            includeSolution
                              ? 'bg-blue-100 text-blue-700 font-medium'
                              : 'text-gray-700 hover:bg-gray-50'
                          }`}
                        >
                          Include solution
                        </button>
                        {mode === 'mock_exam' && (
                          <>
                            <button
                              type="button"
                              onClick={() => setMaxCoverage(!maxCoverage)}
                              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                                maxCoverage
                                  ? 'bg-green-100 text-green-700 font-medium'
                                  : 'text-gray-700 hover:bg-gray-50'
                              }`}
                            >
                              Max Coverage
                            </button>
                            <div className="pt-2 border-t border-gray-200">
                              <label className="block text-xs font-medium text-gray-700 mb-1.5">
                                Question Count
                              </label>
                              <select
                                value={questionCount}
                                onChange={(e) => {
                                  const value = e.target.value
                                  setQuestionCount(value === 'auto' ? 'auto' : parseInt(value))
                                }}
                                className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 mb-2"
                              >
                                <option value="auto">Auto</option>
                                <option value="5">5</option>
                                <option value="8">8</option>
                                <option value="10">10</option>
                                <option value="12">12</option>
                                <option value="15">15</option>
                                <option value="20">20</option>
                                <option value="custom">Custom</option>
                              </select>
                              {questionCount === 'custom' && (
                                <input
                                  type="number"
                                  min="1"
                                  max="50"
                                  value={customQuestionCount}
                                  onChange={(e) => setCustomQuestionCount(parseInt(e.target.value) || 10)}
                                  className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                  placeholder="Enter number"
                                />
                              )}
                            </div>
                            <div className="pt-2 border-t border-gray-200">
                              <label className="block text-xs font-medium text-gray-700 mb-1.5">
                                Weighting
                              </label>
                              <select
                                value={weightingMode}
                                onChange={(e) => setWeightingMode(e.target.value as 'auto' | 'custom' | 'slide_ranges')}
                                className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 mb-2"
                              >
                                <option value="auto">Auto (based on exam type)</option>
                                <option value="custom">Custom weights</option>
                                <option value="slide_ranges">Slide range weights (Advanced)</option>
                              </select>
                              {weightingMode === 'custom' && (
                                <div className="space-y-2">
                                  <div>
                                    <label className="block text-xs text-gray-600 mb-1">Pre-midterm weight</label>
                                    <input
                                      type="number"
                                      step="0.1"
                                      min="0"
                                      value={preMidtermWeight}
                                      onChange={(e) => setPreMidtermWeight(parseFloat(e.target.value) || 1.0)}
                                      className="w-full text-sm px-3 py-1.5 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    />
                                  </div>
                                  <div>
                                    <label className="block text-xs text-gray-600 mb-1">Post-midterm weight</label>
                                    <input
                                      type="number"
                                      step="0.1"
                                      min="0"
                                      value={postMidtermWeight}
                                      onChange={(e) => setPostMidtermWeight(parseFloat(e.target.value) || 2.0)}
                                      className="w-full text-sm px-3 py-1.5 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    />
                                  </div>
                                </div>
                              )}
                              {weightingMode === 'slide_ranges' && (
                                <p className="text-xs text-gray-500 mt-1">
                                  Advanced slide-based weighting coming soon
                                </p>
                              )}
                            </div>
                            <div className="pt-2 border-t border-gray-200">
                              <button
                                type="button"
                                onClick={() => setFocusOnUncertain(!focusOnUncertain)}
                                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                                  focusOnUncertain
                                    ? 'bg-orange-100 text-orange-700 font-medium'
                                    : 'text-gray-700 hover:bg-gray-50'
                                }`}
                              >
                                Focus on uncertain topics
                              </button>
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                    )
                  })()}
                </div>

                {/* Chips for selected options - shown inside textarea area */}
                {(selectedClassId || includeSolution || maxCoverage || mode !== 'normal') && (
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
                            if (mode === 'mock_exam') setMode('normal')
                          }}
                          className="hover:bg-blue-200 rounded-full p-0.5 transition"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </span>
                    )}
                    {mode !== 'normal' && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">
                        Mock Exam
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            setMode('normal')
                          }}
                          className="hover:bg-purple-200 rounded-full p-0.5 transition"
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
                    {maxCoverage && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">
                        Max Coverage
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            setMaxCoverage(false)
                          }}
                          className="hover:bg-green-200 rounded-full p-0.5 transition"
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
                    selectedClassId || includeSolution || maxCoverage ? 'pb-3.5' : 'py-3.5'
                  }`}
                  style={{ maxHeight: '200px' }}
                />
                <div className="absolute right-2 bottom-2 flex items-center gap-1">
                  <button
                    type="submit"
                    disabled={loading || (mode !== 'mock_exam' && !textInput.trim() && files.length === 0)}
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
          {/* Messages Area - scrollable container */}
          <div 
            className="flex-1 overflow-y-auto px-4 py-6 bg-white" 
            style={{ 
              backgroundColor: 'white', 
              minHeight: 0, 
              flex: '1 1 0%', 
              overflowY: 'auto', 
              overflowX: 'hidden',
              WebkitOverflowScrolling: 'touch'
            }}
          >
            <div className="max-w-3xl mx-auto space-y-4" style={{ backgroundColor: 'white' }}>
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
                style={{ backgroundColor: 'transparent' }}
              >
                <div
                  className={`max-w-[85%] ${
                    message.role === 'user' ? 'text-right' : 'text-left'
                  }`}
                  style={{ backgroundColor: 'transparent' }}
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
                        <div className="whitespace-pre-wrap text-sm leading-relaxed text-gray-900 break-words" style={{ wordBreak: 'break-word', overflowWrap: 'break-word', maxWidth: '100%' }}>
                          <LatexRenderer content={message.content} />
                        </div>
                      )}
                    </div>
                  ) : (
                    <>
                      {message.content && (
                        <div className="whitespace-pre-wrap text-sm leading-relaxed text-gray-900 break-words bg-white" style={{ backgroundColor: 'white', wordBreak: 'break-word', overflowWrap: 'break-word', maxWidth: '100%' }}>
                          <LatexRenderer content={message.content} />
                        </div>
                      )}
                      {message.isMaxCoverageSummary && message.result?.questions && (
                        <div className="mt-3">
                          <button
                            onClick={() => {
                              setMessages((prev) =>
                                prev.map((m) =>
                                  m.id === message.id ? { ...m, showPreview: !m.showPreview } : m
                                )
                              )
                            }}
                            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition text-sm font-medium"
                          >
                            {message.showPreview ? 'Hide Exams' : 'Preview Exams'}
                          </button>
                          {message.showPreview && (
                            <div className="mt-3 space-y-4">
                              {message.result.questions.map((exam, idx) => (
                                <div key={idx} className="p-4 border border-gray-200 rounded-lg bg-gray-50">
                                  <h4 className="text-sm font-semibold text-gray-900 mb-2">Mock Exam {idx + 1}</h4>
                                  <div className="text-sm text-gray-700 whitespace-pre-wrap break-words">
                                    <LatexRenderer content={exam} />
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </>
                  )}
                  {message.role === 'assistant' && message.result && (
                    <div className="mt-3 space-y-3" style={{ backgroundColor: 'transparent' }}>
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
                                              {ref.source_file} (score: {ref.score.toFixed(2)}
                                              {ref.coverage !== undefined && ref.coverage !== null ? `, coverage: ${(ref.coverage * 100).toFixed(1)}%` : ''})
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
                                              {ref.source_file} (score: {ref.score.toFixed(2)}
                                              {ref.coverage !== undefined && ref.coverage !== null ? `, coverage: ${(ref.coverage * 100).toFixed(1)}%` : ''})
                                              {isLowScore && <span className="ml-1">⚠</span>}
                                            </li>
                                          )
                                        })}
                                      </ul>
                                    </div>
                                  )}
                                {/* Display total coverage metric for mock exam */}
                                {message.result.metadata?.coverage_metric !== undefined && (
                                  <div className="mt-3 pt-3 border-t border-blue-300">
                                    <p className="font-medium text-blue-900">
                                      Total Coverage: <span className="font-semibold">{(message.result.metadata.coverage_metric * 100).toFixed(1)}%</span>
                                    </p>
                                    <p className="text-blue-700 text-xs mt-1">
                                      Average coverage across all references used in this mock exam
                                    </p>
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
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input Area at bottom when there are messages or text */}
          <div className="border-t border-gray-200 bg-white px-4 py-4 pb-6" style={{ backgroundColor: 'white', flex: '0 0 auto', flexShrink: 0 }}>
        <div className="max-w-3xl mx-auto" style={{ backgroundColor: 'white' }}>
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
              <div className="absolute left-3 bottom-3">
                <button
                  ref={settingsButtonRef}
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
                
                {/* Settings dropdown menu - position dynamically based on available space */}
                {showSettingsMenu && (() => {
                  const buttonRect = settingsButtonRef.current?.getBoundingClientRect()
                  const calculatedMaxHeight = dropdownPosition === 'top' 
                    ? (buttonRect ? Math.min(window.innerHeight * 0.8, buttonRect.top - 20) : 400)
                    : (buttonRect ? Math.min(window.innerHeight * 0.8, window.innerHeight - buttonRect.bottom - 20) : 400)
                  return (
                    <div 
                      ref={settingsMenuRef}
                      className={`absolute ${dropdownPosition === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'} left-0 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-50 p-3 overflow-y-auto`}
                      style={{
                        maxHeight: `${Math.max(calculatedMaxHeight, 200)}px` // Ensure minimum 200px
                      }}
                    >
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
                    <div className="mb-3 pt-2 border-t border-gray-200">
                      <label className="block text-xs font-medium text-gray-700 mb-1.5">
                        Generation Mode
                      </label>
                      <select
                        value={mode}
                        onChange={(e) => {
                          setMode(e.target.value as 'normal' | 'mock_exam')
                        }}
                        className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="normal">Normal</option>
                        <option value="mock_exam" disabled={!selectedClassId}>Mock Exam</option>
                      </select>
                      {mode === 'mock_exam' && !selectedClassId && (
                        <p className="mt-1 text-xs text-gray-500">Select a class to use mock exam mode</p>
                      )}
                    </div>
                    <div className="pt-2 border-t border-gray-200 space-y-2">
                      <button
                        type="button"
                        onClick={() => setIncludeSolution(!includeSolution)}
                        className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                          includeSolution
                            ? 'bg-blue-100 text-blue-700 font-medium'
                            : 'text-gray-700 hover:bg-gray-50'
                        }`}
                      >
                        Include solution
                      </button>
                      {mode === 'mock_exam' && (
                        <>
                          <button
                            type="button"
                            onClick={() => setMaxCoverage(!maxCoverage)}
                            className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                              maxCoverage
                                ? 'bg-green-100 text-green-700 font-medium'
                                : 'text-gray-700 hover:bg-gray-50'
                            }`}
                          >
                            Max Coverage
                          </button>
                          <div className="pt-2 border-t border-gray-200">
                            <label className="block text-xs font-medium text-gray-700 mb-1.5">
                              Question Count
                            </label>
                            <select
                              value={questionCount}
                              onChange={(e) => {
                                const value = e.target.value
                                setQuestionCount(value === 'auto' ? 'auto' : parseInt(value))
                              }}
                              className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 mb-2"
                            >
                              <option value="auto">Auto</option>
                              <option value="5">5</option>
                              <option value="8">8</option>
                              <option value="10">10</option>
                              <option value="12">12</option>
                              <option value="15">15</option>
                              <option value="20">20</option>
                              <option value="custom">Custom</option>
                            </select>
                            {questionCount === 'custom' && (
                              <input
                                type="number"
                                min="1"
                                max="50"
                                value={customQuestionCount}
                                onChange={(e) => setCustomQuestionCount(parseInt(e.target.value) || 10)}
                                className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="Enter number"
                              />
                            )}
                          </div>
                          <div className="pt-2 border-t border-gray-200">
                            <label className="block text-xs font-medium text-gray-700 mb-1.5">
                              Weighting
                            </label>
                            <select
                              value={weightingMode}
                              onChange={(e) => setWeightingMode(e.target.value as 'auto' | 'custom' | 'slide_ranges')}
                              className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 mb-2"
                            >
                              <option value="auto">Auto (based on exam type)</option>
                              <option value="custom">Custom weights</option>
                              <option value="slide_ranges">Slide range weights (Advanced)</option>
                            </select>
                            {weightingMode === 'custom' && (
                              <div className="space-y-2">
                                <div>
                                  <label className="block text-xs text-gray-600 mb-1">Pre-midterm weight</label>
                                  <input
                                    type="number"
                                    step="0.1"
                                    min="0"
                                    value={preMidtermWeight}
                                    onChange={(e) => setPreMidtermWeight(parseFloat(e.target.value) || 1.0)}
                                    className="w-full text-sm px-3 py-1.5 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                  />
                                </div>
                                <div>
                                  <label className="block text-xs text-gray-600 mb-1">Post-midterm weight</label>
                                  <input
                                    type="number"
                                    step="0.1"
                                    min="0"
                                    value={postMidtermWeight}
                                    onChange={(e) => setPostMidtermWeight(parseFloat(e.target.value) || 2.0)}
                                    className="w-full text-sm px-3 py-1.5 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                  />
                                </div>
                              </div>
                            )}
                            {weightingMode === 'slide_ranges' && (
                              <p className="text-xs text-gray-500 mt-1">
                                Advanced slide-based weighting coming soon
                              </p>
                            )}
                          </div>
                          <div className="pt-2 border-t border-gray-200">
                            <button
                              type="button"
                              onClick={() => setFocusOnUncertain(!focusOnUncertain)}
                              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                                focusOnUncertain
                                  ? 'bg-orange-100 text-orange-700 font-medium'
                                  : 'text-gray-700 hover:bg-gray-50'
                              }`}
                            >
                              Focus on uncertain topics
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                    )
                  })()}
              </div>

              {/* Chips for selected options */}
              {(selectedClassId || includeSolution || maxCoverage || mode !== 'normal') && (
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
                          if (mode === 'mock_exam') setMode('normal')
                        }}
                        className="hover:bg-blue-200 rounded-full p-0.5 transition"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </span>
                  )}
                  {mode !== 'normal' && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">
                      Mock Exam
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          setMode('normal')
                        }}
                        className="hover:bg-purple-200 rounded-full p-0.5 transition"
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
                  {maxCoverage && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">
                      Max Coverage
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          setMaxCoverage(false)
                        }}
                        className="hover:bg-green-200 rounded-full p-0.5 transition"
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
                    disabled={loading || (mode !== 'mock_exam' && !textInput.trim() && files.length === 0)}
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
