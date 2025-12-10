import { useState, useRef } from 'react'
import { generateService, GenerateRequest } from '../services/generateService'
import { classService } from '../services/classService'
import { Class } from '../types/class'
import { GenerateResponse } from '../types/question'
import { useEffect } from 'react'

const Generate = () => {
  const [classes, setClasses] = useState<Class[]>([])
  const [selectedClassId, setSelectedClassId] = useState<string>('')
  const [ocrText, setOcrText] = useState('')
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [includeSolution, setIncludeSolution] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<GenerateResponse | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

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

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setImageFile(e.target.files[0])
      setOcrText('') // Clear OCR text when file is selected
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!ocrText && !imageFile) {
      setError('Please provide either OCR text or upload an image')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const request: GenerateRequest = {
        ocr_text: ocrText || undefined,
        image_file: imageFile || undefined,
        include_solution: includeSolution,
        class_id: selectedClassId || undefined,
      }

      const response = await generateService.generate(request)
      setResult(response)

      // Reset form if question was saved to class
      if (response.question_id) {
        setOcrText('')
        setImageFile(null)
        if (fileInputRef.current) {
          fileInputRef.current.value = ''
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate question')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Generate Question</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Input</h2>

          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label htmlFor="class" className="block text-sm font-medium text-gray-700 mb-1">
                Class (Optional - to save question)
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
              <label htmlFor="image" className="block text-sm font-medium text-gray-700 mb-1">
                Upload Image
              </label>
              <input
                ref={fileInputRef}
                type="file"
                id="image"
                accept="image/*"
                onChange={handleFileChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {imageFile && (
                <p className="mt-2 text-sm text-gray-600">Selected: {imageFile.name}</p>
              )}
            </div>

            <div className="mb-4">
              <label htmlFor="ocr_text" className="block text-sm font-medium text-gray-700 mb-1">
                Or Enter OCR Text
              </label>
              <textarea
                id="ocr_text"
                rows={6}
                value={ocrText}
                onChange={(e) => {
                  setOcrText(e.target.value)
                  setImageFile(null) // Clear image when text is entered
                  if (fileInputRef.current) {
                    fileInputRef.current.value = ''
                  }
                }}
                placeholder="Paste extracted text here..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="mb-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={includeSolution}
                  onChange={(e) => setIncludeSolution(e.target.checked)}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Include solution</span>
              </label>
            </div>

            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-800 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || (!ocrText && !imageFile)}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Generating...' : 'Generate Question'}
            </button>
          </form>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Generated Question</h2>

          {result ? (
            <div>
              <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                <pre className="whitespace-pre-wrap text-sm text-gray-900">
                  {result.question}
                </pre>
              </div>

              {result.question_id && (
                <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded text-green-800 text-sm">
                  ✓ Question saved to class successfully!
                </div>
              )}

              <div className="text-xs text-gray-600">
                <p>Processing steps: {result.processing_steps.join(', ')}</p>
                {result.metadata && Object.keys(result.metadata).length > 0 && (
                  <details className="mt-2">
                    <summary className="cursor-pointer">View metadata</summary>
                    <pre className="mt-2 text-xs bg-gray-50 p-2 rounded overflow-auto">
                      {JSON.stringify(result.metadata, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            </div>
          ) : (
            <div className="text-gray-500 text-center py-12">
              Generated question will appear here
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Generate

