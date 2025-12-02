import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const useSessionState = create(
  persist(
    (set, get) => ({
      // Session state
      currentSession: null,
      currentNotebook: null,
      notebooks: [],
      executionResults: {},
      
      // Actions
      setCurrentSession: (session) => set({ currentSession: session }),
      setCurrentNotebook: (notebook) => set({ currentNotebook: notebook }),
      addNotebook: (notebook) => set((state) => ({ 
        notebooks: [...state.notebooks, notebook] 
      })),
      
      // Cell operations
      updateNotebookCell: (notebookId, cellId, updates) => {
        const { notebooks } = get()
        const notebookIndex = notebooks.findIndex(n => n.id === notebookId)
        
        if (notebookIndex === -1) return
        
        const updatedNotebooks = [...notebooks]
        const notebook = { ...updatedNotebooks[notebookIndex] }
        
        const cellIndex = notebook.cells.findIndex(c => c.id === cellId)
        if (cellIndex !== -1) {
          notebook.cells[cellIndex] = { ...notebook.cells[cellIndex], ...updates }
        }
        
        updatedNotebooks[notebookIndex] = notebook
        
        set({ 
          notebooks: updatedNotebooks,
          currentNotebook: notebook.id === get().currentNotebook?.id ? notebook : get().currentNotebook
        })
      },
      
      // Execution results
      setExecutionResult: (cellId, result) => set((state) => ({
        executionResults: { ...state.executionResults, [cellId]: result }
      })),
      
      clearExecutionResults: () => set({ executionResults: {} }),
      
      // Clear all
      clearSession: () => set({ 
        currentSession: null, 
        currentNotebook: null,
        executionResults: {}
      })
    }),
    {
      name: 'autovizai-session-storage',
      partialize: (state) => ({
        currentSession: state.currentSession,
        notebooks: state.notebooks,
        currentNotebook: state.currentNotebook
      })
    }
  )
)

export default useSessionState