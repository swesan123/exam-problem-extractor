import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { classService } from '../services/classService'
import { Class } from '../types/class'
import CreateClassModal from './CreateClassModal'
import DeleteClassModal from './DeleteClassModal'

interface ClassesSidebarProps {
  selectedClassId: string
  onSelectClass: (classId: string) => void
  isOpen: boolean
  onToggle: () => void
  onClassUpdate?: () => void
  onClassNameChange?: (name: string) => void
}

const ClassesSidebar = ({
  selectedClassId,
  onSelectClass,
  isOpen,
  onToggle,
  onClassUpdate,
  onClassNameChange,
}: ClassesSidebarProps) => {
  const navigate = useNavigate()
  const [classes, setClasses] = useState<Class[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [deletingClass, setDeletingClass] = useState<Class | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [hoveredClassId, setHoveredClassId] = useState<string | null>(null)
  const [menuOpenClassId, setMenuOpenClassId] = useState<string | null>(null)

  const loadClasses = async () => {
    try {
      setLoading(true)
      const response = await classService.getAll()
      setClasses(response.classes || [])
    } catch (err) {
      console.error('Failed to load classes:', err)
      setClasses([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadClasses()
  }, [])

  useEffect(() => {
    const saved = localStorage.getItem('sidebarCollapsed')
    if (saved !== null) {
      setIsCollapsed(JSON.parse(saved))
    }
  }, [])

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuOpenClassId) {
        const target = event.target as Node
        // Check if click is outside all menu containers and buttons
        const menuElements = document.querySelectorAll('[data-menu-container]')
        const isClickInsideMenu = Array.from(menuElements).some((el) => el.contains(target))
        if (!isClickInsideMenu) {
          setMenuOpenClassId(null)
        }
      }
    }

    if (menuOpenClassId) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => {
        document.removeEventListener('mousedown', handleClickOutside)
      }
    }
  }, [menuOpenClassId])

  const toggleCollapse = () => {
    const newState = !isCollapsed
    setIsCollapsed(newState)
    localStorage.setItem('sidebarCollapsed', JSON.stringify(newState))
  }

  const handleCreate = async () => {
    await loadClasses()
    setShowCreateModal(false)
    if (onClassUpdate) {
      onClassUpdate()
    }
  }

  const handleDelete = async () => {
    if (deletingClass) {
      await loadClasses()
      if (selectedClassId === deletingClass.id) {
        onSelectClass('')
        if (onClassNameChange) {
          onClassNameChange('')
        }
      }
      setDeletingClass(null)
      if (onClassUpdate) {
        onClassUpdate()
      }
    }
  }

  const handleAddReferences = (classId: string) => {
    navigate(`/classes/${classId}`, { state: { returnTo: '/generate' } })
  }

  const handleViewQuestions = (classId: string) => {
    navigate(`/classes/${classId}/questions`, { state: { returnTo: '/generate' } })
  }

  const filteredClasses = classes.filter((classItem) =>
    classItem.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed left-0 top-0 z-40 p-2 bg-white border-r border-gray-200 rounded-r-lg hover:bg-gray-50 transition"
        title="Open sidebar"
      >
        <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5l7 7-7 7"
          />
        </svg>
      </button>
    )
  }

  if (isCollapsed) {
    return (
      <div className="w-12 bg-white border-r border-gray-200 flex flex-col items-center py-2">
        <button
          onClick={toggleCollapse}
          className="p-2 hover:bg-gray-100 rounded transition mb-2"
          title="Expand sidebar"
        >
          <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </button>
        <button
          onClick={() => setShowCreateModal(true)}
          className="p-2 hover:bg-gray-100 rounded transition"
          title="New Class"
        >
          <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
        </button>
      </div>
    )
  }

  return (
    <>
      <div className="w-64 bg-white flex flex-col h-screen border-r border-gray-200 transition-all duration-300">
        {/* Header */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Classes</h2>
            <div className="flex items-center gap-2">
              <button
                onClick={toggleCollapse}
                className="p-1 hover:bg-gray-100 rounded transition"
                title="Collapse sidebar"
              >
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
                  />
                </svg>
              </button>
              <button
                onClick={onToggle}
                className="p-1 hover:bg-gray-100 rounded transition"
                title="Close sidebar"
              >
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          </div>
          
          {/* New Class Button */}
          <button
            onClick={() => setShowCreateModal(true)}
            className="w-full flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition text-sm text-gray-900"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
            New Class
          </button>

          {/* Search */}
          <div className="mt-3 relative">
            <input
              type="text"
              placeholder="Search classes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-3 py-2 pl-8 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <svg
              className="absolute left-2.5 top-2.5 w-4 h-4 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
        </div>

        {/* Classes List */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-4 text-center text-gray-600 text-sm">Loading classes...</div>
          ) : filteredClasses.length === 0 ? (
            <div className="p-4 text-center text-gray-600 text-sm">
              {searchQuery ? 'No classes found' : 'No classes yet'}
            </div>
          ) : (
            <div className="p-2">
              {filteredClasses.map((classItem) => (
                <div
                  key={classItem.id}
                  className="group relative"
                  onMouseEnter={() => setHoveredClassId(classItem.id)}
                  onMouseLeave={() => setHoveredClassId(null)}
                >
                  <button
                    onClick={() => {
                      const newClassId = classItem.id === selectedClassId ? '' : classItem.id
                      onSelectClass(newClassId)
                      if (onClassNameChange) {
                        onClassNameChange(newClassId ? classItem.name : '')
                      }
                    }}
                    className={`w-full text-left px-3 py-2 rounded-lg mb-1 transition ${
                      selectedClassId === classItem.id
                        ? 'bg-gray-100 text-gray-900'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <div className="text-sm font-medium truncate">{classItem.name}</div>
                  </button>
                  <div className="absolute right-2 top-2" data-menu-container>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setMenuOpenClassId(menuOpenClassId === classItem.id ? null : classItem.id)
                      }}
                      className="p-1 hover:bg-gray-200 rounded text-gray-600 hover:text-gray-900 transition opacity-0 group-hover:opacity-100"
                      title="More options"
                      data-menu-container
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"
                        />
                      </svg>
                    </button>
                    {menuOpenClassId === classItem.id && (
                      <div className="absolute right-0 top-8 w-40 bg-white border border-gray-200 rounded-lg shadow-lg z-50" data-menu-container>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleAddReferences(classItem.id)
                            setMenuOpenClassId(null)
                          }}
                          className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition"
                        >
                          References
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleViewQuestions(classItem.id)
                            setMenuOpenClassId(null)
                          }}
                          className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition"
                        >
                          Questions
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setDeletingClass(classItem)
                            setMenuOpenClassId(null)
                          }}
                          className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition"
                        >
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {showCreateModal && (
        <CreateClassModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={handleCreate}
        />
      )}

      {deletingClass && (
        <DeleteClassModal
          classItem={deletingClass}
          onClose={() => setDeletingClass(null)}
          onSuccess={handleDelete}
        />
      )}
    </>
  )
}

export default ClassesSidebar

