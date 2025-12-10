import { useState } from 'react'
import { classService } from '../services/classService'
import { Class } from '../types/class'

interface DeleteClassModalProps {
  classItem: Class
  onClose: () => void
  onSuccess: () => void
}

const DeleteClassModal = ({ classItem, onClose, onSuccess }: DeleteClassModalProps) => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleDelete = async () => {
    setLoading(true)
    setError(null)

    try {
      await classService.delete(classItem.id)
      onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete class')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Delete Class</h2>

        <p className="text-gray-700 mb-4">
          Are you sure you want to delete the class <strong>{classItem.name}</strong>?
          This action cannot be undone and will also delete all questions in this class.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-800 text-sm">
            {error}
          </div>
        )}

        <div className="flex justify-end space-x-3">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={loading}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
          >
            {loading ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default DeleteClassModal

