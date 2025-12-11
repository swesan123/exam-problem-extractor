import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { questionService } from '../services/questionService'
import { exportService, ExportFormat } from '../services/exportService'
import { Question } from '../types/question'
import { classService } from '../services/classService'
import { Class } from '../types/class'

const ClassQuestions = () => {
  const { id } = useParams<{ id: string }>()
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
        <Link to="/classes" className="mt-2 inline-block text-blue-600 hover:text-blue-800">
          Back to Classes
        </Link>
      </div>
    )
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <Link
        to="/classes"
        className="text-blue-600 hover:text-blue-800 mb-4 inline-block"
      >
        ← Back to Classes
      </Link>

      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{classItem.name}</h1>
          {classItem.subject && (
            <p className="text-gray-600 mt-1">Subject: {classItem.subject}</p>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <select
            onChange={(e) => handleExport(e.target.value as ExportFormat)}
            disabled={exporting || questions.length === 0}
            className="px-4 py-2 border border-gray-300 rounded-md bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <option value="">Export Format...</option>
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
            <div
              key={question.id}
              className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition"
            >
              <div className="flex justify-between items-start mb-2">
                <h3 className="text-lg font-semibold text-gray-900">Question</h3>
                <div className="flex items-center space-x-2">
                <span className="text-xs text-gray-500">
                  {new Date(question.created_at).toLocaleDateString()}
                </span>
                  <div className="flex items-center space-x-1">
                    <select
                      onChange={(e) => handleDownload(question.id, e.target.value as 'txt' | 'pdf' | 'docx' | 'json')}
                      className="text-xs px-2 py-1 border border-gray-300 rounded bg-white text-gray-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <option value="">Download...</option>
                      <option value="txt">TXT</option>
                      <option value="pdf">PDF</option>
                      <option value="docx">DOCX</option>
                      <option value="json">JSON</option>
                    </select>
                    <button
                      onClick={() => handleDelete(question.id)}
                      disabled={deletingId === question.id}
                      className="text-red-600 hover:text-red-800 disabled:opacity-50"
                      title="Delete question"
                    >
                      {deletingId === question.id ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-600"></div>
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
              </div>
              <p className="text-gray-700 whitespace-pre-wrap mb-4">
                {question.question_text}
              </p>
              {question.solution && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <h4 className="text-sm font-semibold text-gray-900 mb-2">Solution</h4>
                  <p className="text-gray-700 whitespace-pre-wrap">{question.solution}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ClassQuestions

