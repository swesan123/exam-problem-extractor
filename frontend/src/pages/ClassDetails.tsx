import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { classService } from '../services/classService'
import { referenceContentService, ReferenceContentItem } from '../services/referenceContentService'
import { Class } from '../types/class'
import AddReferenceContentModal from '../components/AddReferenceContentModal'
import { ReferenceUploadProgress } from '../components/ReferenceUploadProgress'

const ClassDetails = () => {
  const { id } = useParams<{ id: string }>()
  const [classItem, setClassItem] = useState<Class | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [referenceContent, setReferenceContent] = useState<ReferenceContentItem[]>([])
  const [loadingRefContent, setLoadingRefContent] = useState(false)
  const [showAddModal, setShowAddModal] = useState(false)
  const [deletingChunkId, setDeletingChunkId] = useState<string | null>(null)

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
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load class')
      } finally {
        setLoading(false)
      }
    }

    loadClass()
    loadReferenceContent()
  }, [id])

  const handleDeleteReferenceContent = async (chunkId: string) => {
    if (!confirm('Are you sure you want to delete this reference content?')) return

    try {
      setDeletingChunkId(chunkId)
      await referenceContentService.delete(chunkId)
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

        <div className="mt-6 pt-6 border-t border-gray-200">
          <div className="flex justify-between items-center mb-4">
            <div className="text-sm text-gray-600">
              <p>Created: {new Date(classItem.created_at).toLocaleDateString()}</p>
              <p>Updated: {new Date(classItem.updated_at).toLocaleDateString()}</p>
              <p className="mt-2">Questions: {classItem.question_count || 0}</p>
            </div>
            <Link
              to={`/classes/${classItem.id}/questions`}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              View Questions ({classItem.question_count || 0})
            </Link>
          </div>
        </div>

        {/* Reference Content Section */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">
              Reference Content ({referenceContent.length})
            </h2>
            <button
              onClick={() => setShowAddModal(true)}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
            >
              Add Reference Content
            </button>
          </div>

          {loadingRefContent ? (
            <div className="text-center py-4 text-gray-600">Loading reference content...</div>
          ) : referenceContent.length === 0 ? (
            <div className="text-center py-8 bg-gray-50 rounded-lg">
              <p className="text-gray-600 mb-4">No reference content yet.</p>
              <button
                onClick={() => setShowAddModal(true)}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Add Reference Content
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {referenceContent.map((item) => (
                <div
                  key={item.chunk_id}
                  className="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:shadow-md transition"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-2">
                        {item.metadata.source && (
                          <span className="text-sm font-medium text-gray-900">
                            {item.metadata.source}
                          </span>
                        )}
                        {item.metadata.exam_type && (
                          <span className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded">
                            {item.metadata.exam_type}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-700 line-clamp-2">
                        {item.text.substring(0, 200)}
                        {item.text.length > 200 ? '...' : ''}
                      </p>
                      {item.metadata.timestamp && (
                        <p className="text-xs text-gray-500 mt-2">
                          Added: {new Date(item.metadata.timestamp).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={() => handleDeleteReferenceContent(item.chunk_id)}
                      disabled={deletingChunkId === item.chunk_id}
                      className="ml-4 text-red-600 hover:text-red-800 disabled:opacity-50"
                      title="Delete reference content"
                    >
                      {deletingChunkId === item.chunk_id ? (
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
              ))}
            </div>
          )}
        </div>
      </div>

      {showAddModal && id && (
        <AddReferenceContentModal
          classId={id}
          onClose={() => setShowAddModal(false)}
          onSuccess={handleAddSuccess}
        />
      )}

      {id && <ReferenceUploadProgress classId={id} onJobComplete={handleAddSuccess} />}
    </div>
  )
}

export default ClassDetails

