import React, { useState, useRef, useEffect } from 'react'
import { useNotebook } from '../../contexts/NotebookContext'
import NotebookCell from './NotebookCell'
import NotebookToolbar from './NotebookToolbar'
import ExecutionPanel from './ExecutionPanel'
import LoadingSpinner from '../common/LoadingSpinner'
import { Plus, Upload, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'

const InteractiveNotebook = () => {
  const {
    currentNotebook,
    updateNotebookCell,
    executeCell,
    addCell,
    deleteCell,
    createNotebook,
    processInstruction
  } = useNotebook()

  const [executionResults, setExecutionResults] = useState({})
  const [isEditing, setIsEditing] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [showExecutionPanel, setShowExecutionPanel] = useState(false)
  const notebookRef = useRef(null)
  const [activeCell, setActiveCell] = useState(0)

  // Auto-scroll to bottom of notebook when new cell added
  useEffect(() => {
    if (notebookRef.current) {
      // notebookRef.current.scrollTop = notebookRef.current.scrollHeight
    }
  }, [currentNotebook?.cells?.length])

  // Auto-save functionality
  useEffect(() => {
    const autoSave = setTimeout(() => {
      if (currentNotebook && isEditing) {
        console.log('Auto-saving notebook...')
        // In production, you would call an API to save the notebook
      }
    }, 30000) // Auto-save every 30 seconds

    return () => clearTimeout(autoSave)
  }, [currentNotebook, isEditing])

  const handleCellContentChange = (cellId, newContent) => {
    updateNotebookCell(cellId, newContent)
  }

  const handleCellTypeChange = (cellId, newType) => {
    updateNotebookCell(cellId, null, newType)
  }

  const handleExecuteCell = async (cellId) => {
    const result = await executeCell(cellId)
    if (result) {
      setExecutionResults(prev => ({
        ...prev,
        [cellId]: result
      }))
    }
  }

  const handleAddCell = async (index, type) => {
    await addCell(index, type)
  }

  const handleDeleteCell = async (cellId) => {
    await deleteCell(cellId)
  }

  const handleRunAll = async () => {
    if (!currentNotebook || !currentNotebook.cells) return

    toast.loading('Running all cells...')
    setIsProcessing(true)

    try {
      for (const cell of currentNotebook.cells) {
        if (cell.cell_type === 'code' || cell.type === 'code') {
          await handleExecuteCell(cell.id)
        }
      }
      toast.dismiss()
      toast.success('All cells executed successfully')
    } catch (error) {
      toast.dismiss()
      toast.error('Failed to execute all cells')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleAIGenerate = async () => {
    if (!currentNotebook) return

    toast.loading('AI is generating analysis...')
    setIsProcessing(true)

    try {
      await processInstruction('Generate comprehensive data analysis')
      toast.dismiss()
      toast.success('AI analysis generated')
    } catch (error) {
      toast.dismiss()
      toast.error('Failed to generate AI analysis')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleClearOutputs = () => {
    setExecutionResults({})
    toast.success('All outputs cleared')
  }

  const handleExportNotebook = (format) => {
    // Implement export logic
    console.log('Exporting as', format)
  }

  // Ghost Cell Handlers
  const handleAcceptGhost = async (cellId) => {
    const cell = currentNotebook?.cells?.find(c => c.id === cellId)
    if (!cell) return

    // Remove ghost metadata and execute
    const updatedCell = {
      ...cell,
      metadata: {
        ...cell.metadata,
        ghost: false
      }
    }

    // Update cell to remove ghost state
    await updateNotebookCell(cellId, updatedCell.source, updatedCell.cell_type || updatedCell.type)

    // Execute the cell
    await handleExecuteCell(cellId)

    toast.success('Ghost cell accepted and executed')
  }

  const handleRejectGhost = async (cellId) => {
    // Delete the ghost cell
    await deleteCell(cellId)
    toast.success('Ghost cell rejected')
  }

  if (!currentNotebook) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        <div className="text-center">
          <p className="mb-4">No notebook selected</p>
          <button
            onClick={() => createNotebook()}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
          >
            Create New Notebook
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Notebook Toolbar */}
      <NotebookToolbar
        notebook={currentNotebook}
        onExport={handleExportNotebook}
        onToggleEdit={() => setIsEditing(!isEditing)}
        isEditing={isEditing}
        showExecutionPanel={showExecutionPanel}
        onToggleExecutionPanel={() => setShowExecutionPanel(!showExecutionPanel)}
        onRunAll={handleRunAll}
        onAIGenerate={handleAIGenerate}
        onClearOutputs={handleClearOutputs}
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Notebook Cells */}
        <div ref={notebookRef} className="flex-1 overflow-auto bg-white/50">
          <div className="max-w-5xl mx-auto pb-20">
            {currentNotebook.cells.map((cell, index) => (
              <div key={cell.id} className="group/cell-wrapper relative">
                {/* Top Divider (only for first cell) */}
                {index === 0 && (
                  <div className="h-6 opacity-0 hover:opacity-100 transition-opacity flex items-center justify-center gap-2 absolute -top-3 left-0 right-0 z-20 group-hover/cell-wrapper:opacity-100">
                    <div className="h-px bg-border flex-1 mx-4" />
                    <button
                      onClick={() => handleAddCell(0, 'code')}
                      className="flex items-center gap-1 px-3 py-1 text-xs font-medium bg-background border border-border rounded-full shadow-sm hover:bg-muted hover:text-foreground transition-colors text-muted-foreground"
                    >
                      <Plus className="w-3 h-3" /> Code
                    </button>
                    <button
                      onClick={() => handleAddCell(0, 'markdown')}
                      className="flex items-center gap-1 px-3 py-1 text-xs font-medium bg-background border border-border rounded-full shadow-sm hover:bg-muted hover:text-foreground transition-colors text-muted-foreground"
                    >
                      <Plus className="w-3 h-3" /> Text
                    </button>
                    <div className="h-px bg-border flex-1 mx-4" />
                  </div>
                )}

                <NotebookCell
                  cell={cell}
                  isActive={activeCell === cell.id}
                  isEditing={isEditing}
                  executionResult={executionResults[cell.id]}
                  onContentChange={(content) => handleCellContentChange(cell.id, content)}
                  onTypeChange={(type) => handleCellTypeChange(cell.id, type)}
                  onExecute={() => handleExecuteCell(cell.id)}
                  onDelete={() => handleDeleteCell(cell.id)}
                  onAddAbove={() => handleAddCell(index, 'code')}
                  onAddBelow={() => handleAddCell(index + 1, 'code')}
                  onFocus={() => setActiveCell(cell.id)}
                  onAcceptGhost={handleAcceptGhost}
                  onRejectGhost={handleRejectGhost}
                />

                {/* Bottom Divider (Inter-cell) */}
                <div className="h-6 opacity-0 hover:opacity-100 transition-opacity flex items-center justify-center gap-2 absolute -bottom-3 left-0 right-0 z-20 group-hover/cell-wrapper:opacity-100 pointer-events-none hover:pointer-events-auto">
                  <div className="h-px bg-border flex-1 mx-4" />
                  <button
                    onClick={() => handleAddCell(index + 1, 'code')}
                    className="pointer-events-auto flex items-center gap-1 px-3 py-1 text-xs font-medium bg-background border border-border rounded-full shadow-sm hover:bg-muted hover:text-foreground transition-colors text-muted-foreground"
                  >
                    <Plus className="w-3 h-3" /> Code
                  </button>
                  <button
                    onClick={() => handleAddCell(index + 1, 'markdown')}
                    className="pointer-events-auto flex items-center gap-1 px-3 py-1 text-xs font-medium bg-background border border-border rounded-full shadow-sm hover:bg-muted hover:text-foreground transition-colors text-muted-foreground"
                  >
                    <Plus className="w-3 h-3" /> Text
                  </button>
                  <div className="h-px bg-border flex-1 mx-4" />
                </div>
              </div>
            ))}

            {/* Empty State / Bottom Add Buttons */}
            {currentNotebook.cells.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20 gap-4">
                <p className="text-muted-foreground">Start by adding a cell</p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleAddCell(0, 'code')}
                    className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                  >
                    <Plus className="w-4 h-4" /> Code
                  </button>
                  <button
                    onClick={() => handleAddCell(0, 'markdown')}
                    className="flex items-center gap-2 px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/90 transition-colors"
                  >
                    <Plus className="w-4 h-4" /> Text
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Execution Panel */}
        {showExecutionPanel && (
          <div className="hidden lg:block w-80 border-l border-border">
            <ExecutionPanel
              notebook={currentNotebook}
              executionResults={executionResults}
              activeCell={activeCell}
            />
          </div>
        )}
      </div>
    </div>
  )
}

export default InteractiveNotebook