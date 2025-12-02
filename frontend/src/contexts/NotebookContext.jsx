import React, { createContext, useContext, useState, useCallback } from 'react'
import { api } from '../services/api'
import toast from 'react-hot-toast'

const NotebookContext = createContext()

export const useNotebook = () => {
  const context = useContext(NotebookContext)
  if (!context) {
    throw new Error('useNotebook must be used within a NotebookProvider')
  }
  return context
}

export const NotebookProvider = ({ children }) => {
  const [notebooks, setNotebooks] = useState([])
  const [currentNotebook, setCurrentNotebook] = useState(null)
  const [currentSession, setCurrentSession] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

  // --- 1. Create Session from already-uploaded file ---
  const createSession = async (sessionData) => {
    setIsLoading(true)
    try {
      // sessionData is already the response from upload endpoint
      // It contains: { session_id, filename, filepath, dataframe, created_at }

      console.log('Creating session with data:', sessionData)

      if (sessionData && sessionData.session_id) {
        setCurrentSession(sessionData)
        console.log('Session set, attempting to create initial notebook')

        // Auto-Create the first Notebook immediately
        // We pass the session_id explicitly to ensure sync
        await createInitialNotebook(sessionData.session_id)

        console.log('Session creation complete')
        return sessionData
      } else {
        throw new Error('Invalid session data received')
      }
    } catch (error) {
      console.error('Session creation error:', error)
      // Show the actual error message, but don't throw - the session is still valid
      if (error.code !== 'ERR_CANCELED') {
        const errorMsg = error.response?.data?.error || error.message || 'Failed to load dataset'
        console.error('Showing error toast:', errorMsg)
        toast.error(errorMsg)
      }
      // Still return the session data since at least the upload succeeded
      if (sessionData?.session_id) {
        return sessionData
      }
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  // Helper for auto-creation
  const createInitialNotebook = async (sessionId) => {
    try {
      const response = await api.createNotebook({
        session_id: sessionId,
        analysis_type: 'comprehensive_eda',
        user_context: 'Initial data load'
      })

      if (response.data.success) {
        const notebook = response.data.notebook
        setCurrentNotebook(notebook)
        setNotebooks([notebook])
        toast.success(`Analysis Ready: ${notebook.title}`)
      } else {
        console.warn('Notebook creation response:', response.data)
        toast.error(response.data.error || 'Failed to create notebook')
      }
    } catch (error) {
      console.error('Auto-notebook creation failed:', error)
      toast.error(error.response?.data?.error || 'Failed to create initial notebook')
      // We don't throw here to allow the session to exist even if notebook fails
    }
  }

  // --- 2. Manual Notebook Creation ---
  const createNotebook = async (analysisType = 'comprehensive_eda', userContext = '') => {
    if (!currentSession) {
      toast.error('Please upload a dataset first')
      return null
    }

    setIsLoading(true)
    try {
      const response = await api.createNotebook({
        session_id: currentSession.session_id,
        analysis_type: analysisType,
        user_context: userContext
      })

      if (response.data.success) {
        const notebook = response.data.notebook
        setCurrentNotebook(notebook)
        setNotebooks(prev => [...prev, notebook])
        toast.success(`Created notebook: ${notebook.title}`)
        return notebook
      }
    } catch (error) {
      console.error('Notebook creation error:', error)
      toast.error('Failed to create notebook')
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const updateNotebookCell = useCallback(async (cellId, newContent, cellType = null) => {
    if (!currentNotebook || !currentSession) return

    try {
      const response = await api.updateNotebookCell(currentNotebook.notebook_id, {
        session_id: currentSession.session_id,
        cell_id: cellId,
        content: newContent,
        cell_type: cellType
      })

      if (response.data.success) {
        setCurrentNotebook(response.data.notebook)
        return response.data.notebook
      }
    } catch (error) {
      console.error('Cell update error:', error)
    }
  }, [currentNotebook, currentSession])

  const processInstruction = async (instruction) => {
    if (!currentNotebook || !currentSession) return null

    setIsLoading(true)
    try {
      const response = await api.processNotebookInstruction(currentNotebook.notebook_id, {
        session_id: currentSession.session_id,
        instruction: instruction
      })

      if (response.data.success) {
        setCurrentNotebook(response.data.notebook)
        toast.success('Updated')
        return response.data.result
      }
    } catch (error) {
      console.error('Instruction error:', error)
      toast.error('Failed to process instruction')
    } finally {
      setIsLoading(false)
    }
  }

  const executeCell = async (cellId) => {
    if (!currentNotebook || !currentSession) return

    try {
      const response = await api.executeNotebookCell(currentNotebook.notebook_id, {
        session_id: currentSession.session_id,
        cell_id: cellId
      })

      if (response.data.success) {
        // Update the notebook with the one returned from backend (contains new outputs)
        setCurrentNotebook(response.data.notebook)
        return response.data.result
      }
    } catch (error) {
      console.error('Execution error:', error)
      toast.error('Execution failed')
    }
  }

  const addCell = async (index, type = 'code', options = {}) => {
    if (!currentNotebook || !currentSession) return

    try {
      const response = await api.addNotebookCell(currentNotebook.notebook_id, {
        session_id: currentSession.session_id,
        index: index,
        type: type,
        source: options.source || [],
        metadata: options.metadata || {}
      })

      if (response.data.success) {
        setCurrentNotebook(response.data.notebook)
        return response.data.new_cell
      }
    } catch (error) {
      console.error('Add cell error:', error)
      toast.error('Failed to add cell')
    }
  }

  const deleteCell = async (cellId) => {
    if (!currentNotebook || !currentSession) return

    try {
      const response = await api.deleteNotebookCell(currentNotebook.notebook_id, {
        session_id: currentSession.session_id,
        cell_id: cellId
      })

      if (response.data.success) {
        setCurrentNotebook(response.data.notebook)
      }
    } catch (error) {
      console.error('Delete cell error:', error)
      toast.error('Failed to delete cell')
    }
  }

  const clearSession = () => {
    setCurrentSession(null)
    setCurrentNotebook(null)
    setNotebooks([])
    toast.success('Session cleared')
  }

  const value = {
    notebooks,
    currentNotebook,
    currentSession,
    isLoading,
    createSession,
    createNotebook,
    updateNotebookCell,
    processInstruction,
    executeCell,
    addCell,
    deleteCell,
    clearSession,
    setCurrentNotebook
  }

  return (
    <NotebookContext.Provider value={value}>
      {children}
    </NotebookContext.Provider>
  )
}