import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const ReferenceContent = () => {
  const navigate = useNavigate()

  useEffect(() => {
    // Redirect to classes page since reference content is now managed per class
    navigate('/classes', { replace: true })
  }, [navigate])

  return null
}

export default ReferenceContent
