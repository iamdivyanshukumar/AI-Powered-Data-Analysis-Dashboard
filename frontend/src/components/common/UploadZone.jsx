import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { UploadCloud, Loader2 } from 'lucide-react'
import { useNotebook } from '../../contexts/NotebookContext'
import { api } from '../../services/api'
import toast from 'react-hot-toast'

const UploadZone = ({ children, className }) => {
  const [uploading, setUploading] = useState(false)
  const { createSession } = useNotebook()

  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0]
    console.log('onDrop called with files:', acceptedFiles, 'first file:', file)
    
    if (!file) {
      toast.error('No file selected')
      return
    }

    // Validate file type
    if (!file.name.match(/\.(csv|txt)$/i)) {
      toast.error('Only CSV and TXT files are supported')
      return
    }

    setUploading(true)
    const toastId = toast.loading('Uploading dataset...')

    try {
      const formData = new FormData()
      formData.append('file', file)

      console.log('Uploading file:', file.name, 'size:', file.size)
      const response = await api.uploadFile(formData)
      
      console.log('Upload response:', response)
      
      if (response.data.success) {
        console.log('Upload successful, creating session')
        toast.success('Dataset loaded successfully', { id: toastId })
        // Initialize the session with the new data
        await createSession(response.data.session)
      } else {
        console.error('Upload returned success:false', response.data)
        toast.error(response.data.error || 'Failed to upload file', { id: toastId })
      }
    } catch (error) {
      console.error('Upload error details:', error)
      console.error('Error response:', error.response)
      
      // Check if it's a 401 unauthorized error
      if (error.response?.status === 401) {
        toast.error('Session expired. Please login again.', { id: toastId })
        return
      }
      
      const errorMsg = error.response?.data?.error || error.message || 'Failed to upload file'
      toast.error(errorMsg, { id: toastId })
    } finally {
      setUploading(false)
    }
  }, [createSession])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'text/plain': ['.txt']
    },
    multiple: false,
    disabled: uploading
  })

  // 1. Custom Design Wrapper
  if (children) {
    return (
      <div 
        {...getRootProps()} 
        className={`
          cursor-pointer outline-none transition-all relative rounded-2xl
          ${isDragActive ? 'ring-2 ring-primary bg-primary/5' : ''} 
          ${className}
        `}
      >
        <input {...getInputProps()} />
        
        {/* Overlay for drag state to ensure visibility over children */}
        {isDragActive && !uploading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-primary/10 rounded-2xl backdrop-blur-[1px]">
            <p className="text-primary font-medium bg-background/80 px-4 py-2 rounded-full shadow-sm">
              Drop file here
            </p>
          </div>
        )}

        {uploading ? (
           <div className="flex flex-col items-center justify-center py-8 animate-pulse opacity-70">
              <Loader2 className="w-8 h-8 animate-spin mb-2 text-primary" />
              <p className="text-sm font-medium text-muted-foreground">Uploading dataset...</p>
           </div>
        ) : (
           children
        )}
      </div>
    )
  }

  // 2. Default Fallback Design
  return (
    <div
      {...getRootProps()}
      className={`
        border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer
        ${isDragActive ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50 hover:bg-muted/50'}
        ${uploading ? 'opacity-50 pointer-events-none' : ''}
      `}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-3">
        {uploading ? (
          <Loader2 className="w-10 h-10 text-primary animate-spin" />
        ) : (
          <div className={`p-3 rounded-full transition-colors ${isDragActive ? 'bg-primary/20' : 'bg-primary/10'}`}>
            <UploadCloud className={`w-6 h-6 text-primary ${isDragActive ? 'scale-110' : ''} transition-transform`} />
          </div>
        )}
        <div>
          <h3 className="font-medium">
            {uploading ? 'Uploading...' : isDragActive ? 'Drop file now' : 'Click to upload or drag and drop'}
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            CSV or TXT files (max 50MB)
          </p>
        </div>
      </div>
    </div>
  )
}

export default UploadZone