import { useState, useEffect, useRef } from 'react'
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom'
import JSZip from 'jszip'
import { questionService } from '../services/questionService'
import { exportService } from '../services/exportService'
import apiClient from '../services/api'
import { Question } from '../types/question'
import { classService } from '../services/classService'
import { Class } from '../types/class'
import LatexRenderer from '../components/LatexRenderer'

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
  const [deletingAll, setDeletingAll] = useState(false)
  const [downloadingSet, setDownloadingSet] = useState<string | null>(null)
  const [groupByTopic, setGroupByTopic] = useState(false)
  const [expandedTopics, setExpandedTopics] = useState<Set<string>>(new Set())

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

  const handleDeleteAll = async () => {
    if (!id || questions.length === 0) return
    if (!confirm(`Are you sure you want to delete all ${questions.length} question(s)? This action cannot be undone.`)) return

    try {
      setDeletingAll(true)
      setError(null)
      // Delete all questions sequentially
      for (const question of questions) {
        await questionService.delete(question.id)
      }
      // Reload questions (should be empty now)
      const questionsData = await questionService.getByClass(id)
      setQuestions(questionsData.questions)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete all questions')
    } finally {
      setDeletingAll(false)
    }
  }

  const handleDownloadExamSet = async (examSetId: string, exams: Question[]) => {
    try {
      setDownloadingSet(examSetId)
      setError(null)
      
      const zip = new JSZip()
      
      // Download each exam as PDF and add to zip
      for (let idx = 0; idx < exams.length; idx++) {
        const exam = exams[idx]
        try {
          // Use apiClient to download the PDF blob
          const response = await apiClient.get(
            `/api/questions/${exam.id}/download`,
            {
              params: { format: 'pdf', include_solution: false },
              responseType: 'blob',
            }
          )
          
          const blob = response.data
          const examIndex = (exam.metadata?.exam_index as number | undefined) ?? idx
          zip.file(`Mock_Exam_${examIndex + 1}.pdf`, blob)
        } catch (err) {
          console.error(`Failed to download exam ${idx + 1}:`, err)
          // Continue with other exams even if one fails
        }
      }
      
      // Generate zip file
      const zipBlob = await zip.generateAsync({ type: 'blob' })
      const url = window.URL.createObjectURL(zipBlob)
      const link = document.createElement('a')
      link.href = url
      link.download = `Mock_Exams_Set_${examSetId.substring(0, 8)}.zip`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download exam set')
    } finally {
      setDownloadingSet(null)
    }
  }

  const handleDownload = async (questionId: string) => {
    try {
      await questionService.download(questionId, 'pdf', false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download question')
    }
  }

  const handleDownloadAll = async () => {
    if (!id || questions.length === 0) return
    try {
      setExporting(true)
      const blob = await exportService.exportClass(id, 'pdf')
      const filename = `${classItem?.name || 'questions'}.pdf`
      exportService.downloadBlob(blob, filename)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export all questions')
    } finally {
      setExporting(false)
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
          <button
            onClick={handleDownloadAll}
            disabled={exporting || questions.length === 0}
            className="px-4 py-2 border border-gray-300 rounded-md bg-white text-gray-900 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {exporting ? 'Exporting...' : 'Download All as PDF'}
          </button>
          <button
            onClick={handleDeleteAll}
            disabled={deletingAll || questions.length === 0}
            className="px-4 py-2 border border-red-300 rounded-md bg-white text-red-600 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {deletingAll ? 'Deleting...' : 'Delete All Questions'}
          </button>
          {exporting && (
            <span className="text-sm text-gray-600">Exporting...</span>
          )}
        </div>
      </div>

      <div className="mb-4 flex items-center gap-4">
        <input
          type="text"
          placeholder="Search questions..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1 max-w-md px-4 py-2 border border-gray-300 rounded-md bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            checked={groupByTopic}
            onChange={(e) => setGroupByTopic(e.target.checked)}
            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
          />
          Group by topic
        </label>
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
          {(() => {
            // Group max coverage exams by exam_set_id
            const maxCoverageGroups: { [key: string]: Question[] } = {}
            const regularQuestions: Question[] = []
            
            filteredQuestions.forEach((question) => {
              const isMaxCoverage = question.metadata?.is_mock_exam && question.metadata?.exam_type === 'max_coverage'
              const examSetId = question.metadata?.exam_set_id as string | undefined
              
              if (isMaxCoverage && examSetId) {
                if (!maxCoverageGroups[examSetId]) {
                  maxCoverageGroups[examSetId] = []
                }
                maxCoverageGroups[examSetId].push(question)
              } else {
                regularQuestions.push(question)
              }
            })
            
            // Sort grouped exams by exam_index
            Object.keys(maxCoverageGroups).forEach(key => {
              maxCoverageGroups[key].sort((a, b) => {
                const aIndex = (a.metadata?.exam_index as number | undefined) || 0
                const bIndex = (b.metadata?.exam_index as number | undefined) || 0
                return aIndex - bIndex
              })
            })

            // Group regular questions by topic if enabled
            const topicGroups: { [key: string]: Question[] } = {}
            const untaggedQuestions: Question[] = []
            
            if (groupByTopic) {
              regularQuestions.forEach((question) => {
                const topic = question.topic || 'Untagged'
                if (topic === 'Untagged') {
                  untaggedQuestions.push(question)
                } else {
                  if (!topicGroups[topic]) {
                    topicGroups[topic] = []
                  }
                  topicGroups[topic].push(question)
                }
              })
            }
            
            return (
              <>
                {/* Render grouped max coverage exams */}
                {Object.entries(maxCoverageGroups).map(([examSetId, exams]) => {
                  const firstExam = exams[0]
                  const coverageMetric = firstExam.metadata?.coverage_metric || firstExam.metadata?.final_coverage
                  const examType = firstExam.metadata?.exam_type
                  const examIndex = firstExam.metadata?.exam_index
                  const totalExamsInSet = firstExam.metadata?.total_exams_in_set || exams.length
                  
                  return (
                    <div key={examSetId} className="space-y-3 border-l-4 border-green-500 pl-4">
                      <div className="mb-3 pb-3 border-b border-green-200">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-semibold">
                              Max Coverage Exam Set
                            </span>
                            {coverageMetric !== undefined && coverageMetric !== null && (
                              <span className="text-xs text-gray-600">
                                Coverage: {(coverageMetric * 100).toFixed(1)}%
                              </span>
                            )}
                          </div>
                          <button
                            onClick={() => handleDownloadExamSet(examSetId, exams)}
                            disabled={downloadingSet === examSetId}
                            className="px-3 py-1.5 text-xs bg-green-600 text-white rounded hover:bg-green-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {downloadingSet === examSetId ? 'Downloading...' : 'Download All as ZIP'}
                          </button>
                        </div>
                        <p className="text-xs text-gray-600">
                          {totalExamsInSet} exam{totalExamsInSet !== 1 ? 's' : ''} in this set
                        </p>
                      </div>
                      {exams.map((question) => (
                        <QuestionEntry
                          key={question.id}
                          question={question}
                          onDownload={handleDownload}
                          onDelete={handleDelete}
                          deletingId={deletingId}
                        />
                      ))}
                    </div>
                  )
                })}
                {/* Render topic-grouped questions */}
                {groupByTopic && Object.entries(topicGroups).map(([topic, topicQuestions]) => {
                  const isExpanded = expandedTopics.has(topic)
                  return (
                    <div key={topic} className="border-l-4 border-purple-500 pl-4">
                      <button
                        onClick={() => {
                          const newExpanded = new Set(expandedTopics)
                          if (isExpanded) {
                            newExpanded.delete(topic)
                          } else {
                            newExpanded.add(topic)
                          }
                          setExpandedTopics(newExpanded)
                        }}
                        className="w-full text-left mb-2"
                      >
                        <div className="flex items-center justify-between p-3 bg-purple-50 rounded-lg hover:bg-purple-100 transition">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold text-purple-900">{topic}</span>
                            <span className="text-xs text-purple-600">({topicQuestions.length} question{topicQuestions.length !== 1 ? 's' : ''})</span>
                          </div>
                          <svg
                            className={`w-5 h-5 text-purple-600 transition-transform ${isExpanded ? 'transform rotate-180' : ''}`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </div>
                      </button>
                      {isExpanded && (
                        <div className="space-y-3 ml-4">
                          {topicQuestions.map((question) => (
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
                  )
                })}
                {/* Render ungrouped questions (either when topic grouping is off, or untagged questions when it's on) */}
                {(groupByTopic ? untaggedQuestions : regularQuestions).map((question) => (
                  <QuestionEntry
                    key={question.id}
                    question={question}
                    onDownload={handleDownload}
                    onDelete={handleDelete}
                    deletingId={deletingId}
                  />
                ))}
              </>
            )
          })()}
        </div>
      )}
      </div>
    </div>
  )
}

interface QuestionEntryProps {
  question: Question
  onDownload: (id: string) => void
  onDelete: (id: string) => void
  deletingId: string | null
}

const QuestionEntry = ({ question, onDownload, onDelete, deletingId }: QuestionEntryProps) => {
  const [menuOpen, setMenuOpen] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [updatingConfidence, setUpdatingConfidence] = useState(false)
  const [localConfidence, setLocalConfidence] = useState<'confident' | 'uncertain' | 'not_confident' | undefined>(question.user_confidence)
  const [editingTags, setEditingTags] = useState(false)
  const [updatingTags, setUpdatingTags] = useState(false)
  const [tagForm, setTagForm] = useState({
    slideset: question.slideset || '',
    slide: question.slide?.toString() || '',
    topic: question.topic || '',
  })
  const menuRef = useRef<HTMLDivElement>(null)
  
  // Check if this is a mock exam
  const isMockExam = question.metadata && question.metadata.is_mock_exam === true
  const examType = question.metadata?.exam_type as string | undefined
  const examSetId = question.metadata?.exam_set_id as string | undefined
  const examIndex = question.metadata?.exam_index as number | undefined
  const totalExamsInSet = question.metadata?.total_exams_in_set as number | undefined
  const pageReferences = (question.metadata?.page_references as Array<{source_file?: string, page?: number}> | undefined) || []
  const coverageMetric = question.metadata?.coverage_metric as number | undefined

  // Update local confidence when question prop changes
  useEffect(() => {
    setLocalConfidence(question.user_confidence)
  }, [question.user_confidence])

  const handleConfidenceChange = async (confidence: 'confident' | 'uncertain' | 'not_confident') => {
    try {
      setUpdatingConfidence(true)
      setLocalConfidence(confidence)
      await questionService.update(question.id, { user_confidence: confidence })
      // Optionally reload questions to get updated data
    } catch (err) {
      console.error('Failed to update confidence:', err)
      setLocalConfidence(question.user_confidence) // Revert on error
    } finally {
      setUpdatingConfidence(false)
    }
  }

  const handleSaveTags = async () => {
    try {
      setUpdatingTags(true)
      await questionService.update(question.id, {
        slideset: tagForm.slideset || undefined,
        slide: tagForm.slide ? parseInt(tagForm.slide) : undefined,
        topic: tagForm.topic || undefined,
      })
      setEditingTags(false)
      // Optionally reload questions to get updated data
    } catch (err) {
      console.error('Failed to update tags:', err)
    } finally {
      setUpdatingTags(false)
    }
  }

  const handleCancelTags = () => {
    setTagForm({
      slideset: question.slideset || '',
      slide: question.slide?.toString() || '',
      topic: question.topic || '',
    })
    setEditingTags(false)
  }

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
    // Check if this looks like a mock exam (starts with # heading)
    if (text.trim().startsWith('#')) {
      const lines = text.split('\n')
      const firstLine = lines[0].replace(/^#+\s*/, '').trim()
      if (firstLine.length > 60) return firstLine.substring(0, 60) + '...'
      return firstLine || 'Mock Exam'
    }
    
    const lines = text.split('\n')
    // Remove markdown bold (**text**) and LaTeX delimiters for preview
    const firstLine = lines[0]
      .replace(/\*\*([^*]+)\*\*/g, '$1') // Remove markdown bold
      .replace(/\\?[\(\[].*?\\?[\)\]]/g, '') // Remove LaTeX math
      .replace(/\$.*?\$/g, '') // Remove $ math
      .trim()
    if (firstLine.length > 60) return firstLine.substring(0, 60) + '...'
    return firstLine || 'Question'
  }

  const getQuestionPreview = (text: string, maxLength: number = 100) => {
    // Remove markdown and LaTeX for preview
    const cleaned = text
      .replace(/^#+\s*/gm, '') // Remove markdown headings (#, ##, ###, etc.)
      .replace(/\*\*([^*]+)\*\*/g, '$1') // Remove markdown bold
      .replace(/\*([^*]+)\*/g, '$1') // Remove markdown italic
      .replace(/`([^`]+)`/g, '$1') // Remove inline code
      .replace(/\\?[\(\[].*?\\?[\)\]]/g, '') // Remove LaTeX math
      .replace(/\$.*?\$/g, '') // Remove $ math
      .replace(/---+/g, '') // Remove horizontal rules
      .replace(/\n+/g, ' ') // Replace newlines with spaces
      .trim()
    if (cleaned.length <= maxLength) return cleaned
    return cleaned.substring(0, maxLength) + '...'
  }

  return (
    <div className={`bg-white rounded-lg border ${isMockExam ? 'border-purple-300' : 'border-gray-200'} p-5 hover:shadow-md transition`}>
      {isMockExam && examType === 'max_coverage' && examIndex === 0 && (
        <div className="mb-3 pb-3 border-b border-purple-200">
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-semibold">
              Max Coverage Exam Set
            </span>
            {coverageMetric !== undefined && coverageMetric !== null && (
              <span className="text-xs text-gray-600">
                Coverage: {(coverageMetric * 100).toFixed(1)}%
              </span>
            )}
          </div>
          <p className="text-xs text-gray-600">
            {totalExamsInSet ?? 1} exam{(totalExamsInSet ?? 1) !== 1 ? 's' : ''} in this set
          </p>
        </div>
      )}
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0 cursor-pointer" onClick={() => setExpanded(!expanded)}>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-base font-semibold text-gray-900">
              {isMockExam 
                ? (examType === 'max_coverage' 
                    ? `Mock Exam ${(examIndex ?? 0) + 1} of ${totalExamsInSet ?? 1}`
                    : 'Mock Exam')
                : getQuestionName(question.question_text)}
            </h3>
            {isMockExam && (
              <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs font-medium">
                Mock Exam
              </span>
            )}
          </div>
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
                <LatexRenderer content={question.question_text} />
              </div>
              {question.solution && !isMockExam && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <h4 className="text-sm font-semibold text-gray-900 mb-2">Solution</h4>
                  <div className="text-sm text-gray-700 whitespace-pre-wrap">
                    <LatexRenderer content={question.solution} />
                  </div>
                </div>
              )}
              {/* Page references */}
              {pageReferences.length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <h4 className="text-sm font-semibold text-gray-900 mb-2">Page References</h4>
                  <div className="text-xs text-gray-600 space-y-1">
                    {pageReferences.map((ref, idx: number) => (
                      <div key={idx} className="flex items-center gap-2">
                        <span>
                          {ref.source_file || 'unknown'} (page {ref.page ?? '?'})
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {/* Tags (slideset, slide, topic) */}
              <div className="mt-4 pt-4 border-t border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold text-gray-900">Tags</h4>
                  {!editingTags && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setEditingTags(true)
                      }}
                      className="text-xs text-blue-600 hover:text-blue-800"
                    >
                      Edit
                    </button>
                  )}
                </div>
                {editingTags ? (
                  <div className="space-y-3">
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">Slideset</label>
                      <input
                        type="text"
                        value={tagForm.slideset}
                        onChange={(e) => setTagForm({ ...tagForm, slideset: e.target.value })}
                        className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., Lecture_5"
                        onClick={(e) => e.stopPropagation()}
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">Slide Number</label>
                      <input
                        type="number"
                        min="1"
                        value={tagForm.slide}
                        onChange={(e) => setTagForm({ ...tagForm, slide: e.target.value })}
                        className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., 12"
                        onClick={(e) => e.stopPropagation()}
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">Topic</label>
                      <input
                        type="text"
                        value={tagForm.topic}
                        onChange={(e) => setTagForm({ ...tagForm, topic: e.target.value })}
                        className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., Linear Algebra"
                        onClick={(e) => e.stopPropagation()}
                      />
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleSaveTags()
                        }}
                        disabled={updatingTags}
                        className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition disabled:opacity-50"
                      >
                        {updatingTags ? 'Saving...' : 'Save'}
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleCancelTags()
                        }}
                        disabled={updatingTags}
                        className="px-3 py-1.5 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition disabled:opacity-50"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2 text-xs">
                    {question.slideset ? (
                      <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded">
                        Slideset: {question.slideset}
                      </span>
                    ) : (
                      <span className="px-2 py-1 bg-gray-100 text-gray-500 rounded italic">
                        No slideset
                      </span>
                    )}
                    {question.slide !== undefined ? (
                      <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded">
                        Slide: {question.slide}
                      </span>
                    ) : (
                      <span className="px-2 py-1 bg-gray-100 text-gray-500 rounded italic">
                        No slide
                      </span>
                    )}
                    {question.topic ? (
                      <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded">
                        Topic: {question.topic}
                      </span>
                    ) : (
                      <span className="px-2 py-1 bg-gray-100 text-gray-500 rounded italic">
                        No topic
                      </span>
                    )}
                  </div>
                )}
              </div>
              {/* Confidence selector */}
              <div className="mt-4 pt-4 border-t border-gray-200">
                <h4 className="text-sm font-semibold text-gray-900 mb-2">Confidence</h4>
                <div className="flex items-center gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleConfidenceChange('confident')
                    }}
                    disabled={updatingConfidence}
                    className={`px-3 py-1.5 rounded text-sm font-medium transition ${
                      localConfidence === 'confident'
                        ? 'bg-green-100 text-green-700 border-2 border-green-500'
                        : 'bg-gray-100 text-gray-600 border-2 border-transparent hover:bg-gray-200'
                    } disabled:opacity-50`}
                    title="Confident (✓)"
                  >
                    ✓ Confident
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleConfidenceChange('uncertain')
                    }}
                    disabled={updatingConfidence}
                    className={`px-3 py-1.5 rounded text-sm font-medium transition ${
                      localConfidence === 'uncertain'
                        ? 'bg-yellow-100 text-yellow-700 border-2 border-yellow-500'
                        : 'bg-gray-100 text-gray-600 border-2 border-transparent hover:bg-gray-200'
                    } disabled:opacity-50`}
                    title="Uncertain (~)"
                  >
                    ~ Uncertain
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleConfidenceChange('not_confident')
                    }}
                    disabled={updatingConfidence}
                    className={`px-3 py-1.5 rounded text-sm font-medium transition ${
                      localConfidence === 'not_confident'
                        ? 'bg-red-100 text-red-700 border-2 border-red-500'
                        : 'bg-gray-100 text-gray-600 border-2 border-transparent hover:bg-gray-200'
                    } disabled:opacity-50`}
                    title="Not Confident (✗)"
                  >
                    ✗ Not Confident
                  </button>
                </div>
              </div>
              {/* Coverage metric for mock exams */}
              {isMockExam && coverageMetric !== undefined && coverageMetric !== null && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <p className="text-xs text-gray-600">
                    Coverage: <span className="font-semibold">{(coverageMetric * 100).toFixed(1)}%</span>
                  </p>
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
                    onDownload(question.id)
                    setMenuOpen(false)
                  }}
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition"
                >
                  Download PDF
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

