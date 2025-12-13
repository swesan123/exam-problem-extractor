import { useState, useEffect, useRef } from 'react'
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom'
import { questionService } from '../services/questionService'
import { exportService, ExportFormat } from '../services/exportService'
import { Question } from '../types/question'
import { classService } from '../services/classService'
import { Class } from '../types/class'

const ClassQuestions = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const returnTo = (location.state as { returnTo?: string })?.returnTo || '/classes'
  const [classItem, setClassItem] = useState<Class | null>(null)
  const [questions, setQuestions] = useState<Question[]>([])
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    const loadData = async () => {
      if (!id) return

      try {
        setLoading(true)
        setError(null)

        // Load class and questions in parallel
        const [classData, questionsData] = await Promise.all([
          classService.getById(id),
          questionService.getByClass(id),
        ])

        setClassItem(classData)
        setQuestions(questionsData.questions)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data')
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [id])

  const handleExport = async (format: ExportFormat) => {
    if (!id) return

    try {
      setExporting(true)
      const blob = await exportService.exportClass(id, format)
      const filename = `${classItem?.name || 'questions'}.${format}`
      exportService.downloadBlob(blob, filename)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export questions')
    } finally {
      setExporting(false)
    }
  }

  const handleDelete = async (questionId: string) => {
    if (!confirm('Are you sure you want to delete this question?')) return

    try {
      setDeletingId(questionId)
      await questionService.delete(questionId)
      // Reload questions
      const questionsData = await questionService.getByClass(id!)
      setQuestions(questionsData.questions)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete question')
    } finally {
      setDeletingId(null)
    }
  }

  const handleDownload = async (questionId: string, format: 'txt' | 'pdf' | 'docx' | 'json' = 'txt') => {
    try {
      await questionService.download(questionId, format, false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download question')
    }
  }

  const filteredQuestions = questions.filter((q) =>
    q.question_text.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-600">Loading questions...</div>
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

  const handleDownloadAll = async (format: ExportFormat) => {
    if (!id || questions.length === 0) return
    try {
      setExporting(true)
      const blob = await exportService.exportClass(id, format)
      const filename = `${classItem?.name || 'questions'}.${format}`
      exportService.downloadBlob(blob, filename)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export all questions')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <div className="px-6 py-6 sm:px-8 flex-1 overflow-y-auto">
      <button
        onClick={() => navigate(returnTo)}
        className="text-blue-600 hover:text-blue-800 mb-4 inline-block"
      >
        ← Back
      </button>

      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">{classItem.name}</h1>
        {classItem.subject && (
          <p className="text-gray-600">Subject: {classItem.subject}</p>
        )}
      </div>

      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center space-x-2">
          <select
            onChange={(e) => {
              const format = e.target.value as ExportFormat
              if (format) {
                handleDownloadAll(format)
                e.target.value = ''
              }
            }}
            disabled={exporting || questions.length === 0}
            className="px-4 py-2 border border-gray-300 rounded-md bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <option value="">Download All...</option>
            <option value="txt">TXT</option>
            <option value="pdf">PDF</option>
            <option value="docx">DOCX</option>
            <option value="json">JSON</option>
          </select>
          {exporting && (
            <span className="text-sm text-gray-600">Exporting...</span>
          )}
        </div>
      </div>

      <div className="mb-4">
        <input
          type="text"
          placeholder="Search questions..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-md bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="mb-4 text-sm text-gray-600">
        Showing {filteredQuestions.length} of {questions.length} questions
      </div>

      {filteredQuestions.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          {questions.length === 0 ? (
            <>
              <p className="text-gray-600 mb-4">No questions found in this class.</p>
              <Link
                to="/generate"
                className="text-blue-600 hover:text-blue-800 font-medium"
              >
                Generate your first question
              </Link>
            </>
          ) : (
            <p className="text-gray-600">No questions match your search.</p>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredQuestions.map((question) => (
            <QuestionEntry
              key={question.id}
              question={question}
              onDownload={handleDownload}
              onDelete={handleDelete}
              deletingId={deletingId}
            />
          ))}
        </div>
      )}
      </div>
    </div>
  )
}

interface QuestionEntryProps {
  question: Question
  onDownload: (id: string, format: 'txt' | 'pdf' | 'docx' | 'json') => void
  onDelete: (id: string) => void
  deletingId: string | null
}

const QuestionEntry = ({ question, onDownload, onDelete, deletingId }: QuestionEntryProps) => {
  const [menuOpen, setMenuOpen] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuOpen && menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false)
      }
    }

    if (menuOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => {
        document.removeEventListener('mousedown', handleClickOutside)
      }
    }
  }, [menuOpen])

  const getQuestionName = (text: string) => {
    const lines = text.split('\n')
    const firstLine = lines[0].replace(/\*\*/g, '').trim()
    if (firstLine.length > 60) return firstLine.substring(0, 60) + '...'
    return firstLine || 'Question'
  }

  const getQuestionPreview = (text: string, maxLength: number = 100) => {
    const cleaned = text.replace(/\*\*/g, '').replace(/\n/g, ' ').trim()
    if (cleaned.length <= maxLength) return cleaned
    return cleaned.substring(0, maxLength) + '...'
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5 hover:shadow-md transition">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0 cursor-pointer" onClick={() => setExpanded(!expanded)}>
          <h3 className="text-base font-semibold text-gray-900 mb-1">
            {getQuestionName(question.question_text)}
          </h3>
          {!expanded ? (
            <>
              <p className="text-sm text-gray-600 mb-2">
                {getQuestionPreview(question.question_text)}
              </p>
              <span className="text-xs text-gray-500">
                {new Date(question.created_at).toLocaleDateString()}
              </span>
            </>
          ) : (
            <div className="mt-2">
              <div className="text-sm text-gray-700 whitespace-pre-wrap mb-3">
                {question.question_text}
              </div>
              {question.solution && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <h4 className="text-sm font-semibold text-gray-900 mb-2">Solution</h4>
                  <p className="text-sm text-gray-700 whitespace-pre-wrap">{question.solution}</p>
                </div>
              )}
              <span className="text-xs text-gray-500 mt-3 block">
                {new Date(question.created_at).toLocaleDateString()}
              </span>
            </div>
          )}
        </div>
        <div className="relative ml-4" ref={menuRef}>
          <button
            onClick={(e) => {
              e.stopPropagation()
              setMenuOpen(!menuOpen)
            }}
            className="p-1 hover:bg-gray-100 rounded text-gray-600 hover:text-gray-900 transition"
            title="More options"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"
              />
            </svg>
          </button>
          {menuOpen && (
            <div className="absolute right-0 top-8 w-40 bg-white border border-gray-200 rounded-lg shadow-lg z-50" onClick={(e) => e.stopPropagation()}>
              <div className="border-b border-gray-200">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onDownload(question.id, 'txt')
                    setMenuOpen(false)
                  }}
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition"
                >
                  Download TXT
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onDownload(question.id, 'pdf')
                    setMenuOpen(false)
                  }}
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition"
                >
                  Download PDF
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onDownload(question.id, 'docx')
                    setMenuOpen(false)
                  }}
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition"
                >
                  Download DOCX
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onDownload(question.id, 'json')
                    setMenuOpen(false)
                  }}
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition"
                >
                  Download JSON
                </button>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  if (confirm('Are you sure you want to delete this question?')) {
                    onDelete(question.id)
                    setMenuOpen(false)
                  }
                }}
                disabled={deletingId === question.id}
                className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition disabled:opacity-50"
              >
                {deletingId === question.id ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ClassQuestions

