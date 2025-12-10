import { useState, useEffect } from 'react'
import { embedService } from '../services/embedService'
import { classService } from '../services/classService'
import { Class } from '../types/class'
import { EmbeddingRequest } from '../types/embedding'

const ReferenceContent = () => {
  const [classes, setClasses] = useState<Class[]>([])
  const [selectedClassId, setSelectedClassId] = useState<string>('')
  const [text, setText] = useState('')
  const [examSource, setExamSource] = useState('')
  const [examType, setExamType] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    const loadClasses = async () => {
      try {
        const response = await classService.getAll()
        setClasses(response.classes)
      } catch (err) {
        console.error('Failed to load classes:', err)
      }
    }
    loadClasses()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!text.trim()) {
      setError('Please enter reference text')
      return
    }

    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      // Generate a unique chunk ID
      const chunkId = `chunk_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      
      const request: EmbeddingRequest = {
        text: text.trim(),
        metadata: {
          source: examSource || 'manual_upload',
          chunk_id: chunkId,
          page: undefined,
          exam_type: examType || undefined,
          class_id: selectedClassId || undefined,
        },
      }

      const response = await embedService.embedText(request)
      setSuccess(`Reference content embedded successfully! Embedding ID: ${response.embedding_id}`)
      
      // Reset form
      setText('')
      setExamSource('')
      setExamType('')
      setSelectedClassId('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to embed reference content')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Add Reference Content</h1>

      <div className="bg-white rounded-lg shadow p-6 max-w-3xl">
        <p className="text-gray-600 mb-6">
          Add practice exams, test questions, or other reference material. This content will be used 
          to improve question generation through semantic search.
        </p>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="class" className="block text-sm font-medium text-gray-700 mb-1">
              Class (Optional - to associate with a class)
            </label>
            <select
              id="class"
              value={selectedClassId}
              onChange={(e) => setSelectedClassId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a class...</option>
              {classes.map((classItem) => (
                <option key={classItem.id} value={classItem.id}>
                  {classItem.name}
                </option>
              ))}
            </select>
          </div>

          <div className="mb-4">
            <label htmlFor="exam_source" className="block text-sm font-medium text-gray-700 mb-1">
              Exam Source (Optional)
            </label>
            <input
              type="text"
              id="exam_source"
              value={examSource}
              onChange={(e) => setExamSource(e.target.value)}
              placeholder="e.g., '2023 Final Exam', 'Practice Test 1'"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="mb-4">
            <label htmlFor="exam_type" className="block text-sm font-medium text-gray-700 mb-1">
              Exam Type (Optional)
            </label>
            <select
              id="exam_type"
              value={examType}
              onChange={(e) => setExamType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select type...</option>
              <option value="practice_exam">Practice Exam</option>
              <option value="test">Test</option>
              <option value="quiz">Quiz</option>
              <option value="homework">Homework</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div className="mb-4">
            <label htmlFor="text" className="block text-sm font-medium text-gray-700 mb-1">
              Reference Text *
            </label>
            <textarea
              id="text"
              rows={12}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste reference exam questions, practice problems, or other content here..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
            <p className="mt-1 text-sm text-gray-500">
              The text will be automatically chunked and embedded for semantic search.
            </p>
          </div>

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

          <button
            type="submit"
            disabled={loading || !text.trim()}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Embedding...' : 'Add Reference Content'}
          </button>
        </form>
      </div>

      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-blue-900 mb-2">How it works:</h3>
        <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
          <li>Reference content is embedded into a vector database</li>
          <li>When generating questions, similar content is retrieved automatically</li>
          <li>This helps generate questions in the same style and format</li>
          <li>You can add multiple reference documents for better results</li>
        </ul>
      </div>
    </div>
  )
}

export default ReferenceContent

