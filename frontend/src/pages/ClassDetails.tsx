import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { classService } from '../services/classService'
import { Class } from '../types/class'

const ClassDetails = () => {
  const { id } = useParams<{ id: string }>()
  const [classItem, setClassItem] = useState<Class | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
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
  }, [id])

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
          <div className="text-sm text-gray-600">
            <p>Created: {new Date(classItem.created_at).toLocaleDateString()}</p>
            <p>Updated: {new Date(classItem.updated_at).toLocaleDateString()}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ClassDetails

