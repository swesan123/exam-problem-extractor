import { useEffect, useRef, useState } from 'react'
import { jobService, JobStatus } from '../services/jobService'

interface ReferenceUploadProgressProps {
  classId: string
  onJobComplete?: () => void
}

export function ReferenceUploadProgress({
  classId,
  onJobComplete,
}: ReferenceUploadProgressProps) {
  const [activeJobs, setActiveJobs] = useState<JobStatus[]>([])
  const [isExpanded, setIsExpanded] = useState(false)
  const prevActiveCountRef = useRef(0)

  // Load active jobs for this class
  useEffect(() => {
    const loadJobs = async () => {
      try {
        const response = await jobService.listClassJobs(classId)
        const active = response.jobs.filter(
          (job) => job.status === 'pending' || job.status === 'processing'
        )
        
        // Poll each active job
        const jobStatuses = await Promise.all(
          active.map((job) => jobService.getJobStatus(job.job_id))
        )
        setActiveJobs(jobStatuses)

        if (active.length === 0 && prevActiveCountRef.current > 0 && onJobComplete) {
          onJobComplete()
        }
        prevActiveCountRef.current = active.length
      } catch (error) {
        console.error('Failed to load jobs:', error)
      }
    }

    loadJobs()
    const interval = setInterval(loadJobs, 3000) // Refresh every 3 seconds

    return () => clearInterval(interval)
  }, [classId, onJobComplete])

  if (activeJobs.length === 0) {
    return null
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'processing':
        return 'bg-yellow-500'
      case 'completed':
        return 'bg-green-500'
      case 'failed':
        return 'bg-red-500'
      default:
        return 'bg-gray-500'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'processing':
        return 'Processing'
      case 'completed':
        return 'Completed'
      case 'failed':
        return 'Failed'
      default:
        return 'Pending'
    }
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-md">
      <div
        className={`bg-white rounded-lg shadow-lg border-2 ${
          isExpanded ? 'border-blue-500' : 'border-gray-300'
        }`}
      >
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 rounded-t-lg"
        >
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${getStatusColor(activeJobs[0]?.status || 'pending')}`} />
            <span className="font-semibold text-sm">
              {activeJobs.length} job{activeJobs.length > 1 ? 's' : ''} processing
            </span>
          </div>
          <span className="text-xs text-gray-500">
            {isExpanded ? '▼' : '▲'}
          </span>
        </button>

        {isExpanded && (
          <div className="px-4 py-3 border-t border-gray-200 max-h-96 overflow-y-auto">
            {activeJobs.map((job) => (
              <div key={job.job_id} className="mb-4 last:mb-0">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">
                    {getStatusText(job.status)}
                  </span>
                  <span className="text-xs text-gray-500">
                    {job.processed_files}/{job.total_files} files
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                  <div
                    className={`h-2 rounded-full transition-all ${getStatusColor(job.status)}`}
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
                {job.failed_files > 0 && (
                  <p className="text-xs text-red-600">
                    {job.failed_files} file{job.failed_files > 1 ? 's' : ''} failed
                  </p>
                )}
                {job.error_message && (
                  <p className="text-xs text-red-600 mt-1">{job.error_message}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

