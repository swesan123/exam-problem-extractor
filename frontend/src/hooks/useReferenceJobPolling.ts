import { useEffect, useState, useRef } from 'react'
import { jobService, JobStatus } from '../services/jobService'

interface UseReferenceJobPollingOptions {
  jobId: string | null
  enabled?: boolean
  pollInterval?: number
  onComplete?: (job: JobStatus) => void
  onError?: (error: Error) => void
}

export function useReferenceJobPolling({
  jobId,
  enabled = true,
  pollInterval = 2000,
  onComplete,
  onError,
}: UseReferenceJobPollingOptions) {
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (!jobId || !enabled) {
      return
    }

    const poll = async () => {
      try {
        const status = await jobService.getJobStatus(jobId)
        setJobStatus(status)
        setError(null)

        // Stop polling if completed or failed
        if (status.status === 'completed' || status.status === 'failed') {
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
          }
          if (status.status === 'completed' && onComplete) {
            onComplete(status)
          }
          if (status.status === 'failed' && onError) {
            onError(new Error(status.error_message || 'Job failed'))
          }
        }
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to poll job status')
        setError(error)
        if (onError) {
          onError(error)
        }
        // Stop polling on error
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = null
        }
      }
    }

    // Initial poll
    poll()

    // Set up polling interval
    intervalRef.current = setInterval(poll, pollInterval)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [jobId, enabled, pollInterval, onComplete, onError])

  return { jobStatus, error }
}

