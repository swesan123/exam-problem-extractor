import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { classService } from '../services/classService'
import { Class } from '../types/class'
import CreateClassModal from '../components/CreateClassModal'
import EditClassModal from '../components/EditClassModal'
import DeleteClassModal from '../components/DeleteClassModal'

const Classes = () => {
  const [classes, setClasses] = useState<Class[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingClass, setEditingClass] = useState<Class | null>(null)
  const [deletingClass, setDeletingClass] = useState<Class | null>(null)

  const loadClasses = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await classService.getAll()
      setClasses(response.classes)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load classes')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadClasses()
  }, [])

  const handleCreate = async () => {
    await loadClasses()
    setShowCreateModal(false)
  }

  const handleEdit = async () => {
    await loadClasses()
    setEditingClass(null)
  }

  const handleDelete = async () => {
    await loadClasses()
    setDeletingClass(null)
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-600">Loading classes...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">Error: {error}</p>
        <button
          onClick={loadClasses}
          className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Classes</h1>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          Create Class
        </button>
      </div>

      {classes.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <p className="text-gray-600 mb-4">No classes found.</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Create Your First Class
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {classes.map((classItem) => (
            <div
              key={classItem.id}
              className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition"
            >
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                {classItem.name}
              </h2>
              {classItem.subject && (
                <p className="text-sm text-gray-600 mb-2">
                  Subject: {classItem.subject}
                </p>
              )}
              {classItem.description && (
                <p className="text-gray-700 mb-4 line-clamp-2">
                  {classItem.description}
                </p>
              )}
              <div className="flex justify-between items-center mt-4">
                <Link
                  to={`/classes/${classItem.id}`}
                  className="text-blue-600 hover:text-blue-800 font-medium"
                >
                  View Details
                </Link>
                <div className="flex space-x-2">
                  <button
                    onClick={() => setEditingClass(classItem)}
                    className="text-gray-600 hover:text-gray-900"
                    title="Edit"
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
                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                      />
                    </svg>
                  </button>
                  <button
                    onClick={() => setDeletingClass(classItem)}
                    className="text-red-600 hover:text-red-900"
                    title="Delete"
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
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreateModal && (
        <CreateClassModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={handleCreate}
        />
      )}

      {editingClass && (
        <EditClassModal
          classItem={editingClass}
          onClose={() => setEditingClass(null)}
          onSuccess={handleEdit}
        />
      )}

      {deletingClass && (
        <DeleteClassModal
          classItem={deletingClass}
          onClose={() => setDeletingClass(null)}
          onSuccess={handleDelete}
        />
      )}
    </div>
  )
}

export default Classes

