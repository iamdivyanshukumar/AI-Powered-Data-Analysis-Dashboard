import React, { useState } from 'react'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import DataDeck from '../ContextPanel/DataDeck'
import InteractiveNotebook from '../Notebook/InteractiveNotebook'
import ChatInterface from '../AgentPanel/ChatInterface'
import InstructionProcessor from '../Notebook/InstructionProcessor'
import { useNotebook } from '../../contexts/NotebookContext'
import { Menu, X, Database, MessageSquare, Code } from 'lucide-react'

const ThreePanelLayout = () => {
  const { currentNotebook, currentSession, addCell } = useNotebook()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [activePanel, setActivePanel] = useState('notebook') // 'context', 'notebook', 'agent'

  // Handler to add Ghost Cells from AI to the notebook
  const handleGhostCellsGenerated = async (proposedCells) => {
    if (!currentNotebook || !proposedCells || proposedCells.length === 0) return

    // Add each Ghost Cell to the end of the notebook
    for (const ghostCell of proposedCells) {
      const cellIndex = currentNotebook.cells?.length || 0
      await addCell(cellIndex, ghostCell.cell_type || 'code', {
        source: ghostCell.source,
        metadata: ghostCell.metadata || { ghost: true }
      })
    }
  }

  // Mobile view - show only one panel at a time
  if (window.innerWidth < 768) {
    return (
      <div className="h-screen flex flex-col bg-background">
        {/* Mobile Header */}
        <header className="border-b border-border bg-card p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="p-2 hover:bg-muted rounded-lg transition-colors"
              >
                {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </button>
              <div>
                <h1 className="font-semibold text-foreground">AutoVizAI</h1>
                <p className="text-xs text-muted-foreground">{currentSession?.filename}</p>
              </div>
            </div>
          </div>

          {/* Mobile Navigation */}
          {isMobileMenuOpen && (
            <div className="mt-4 grid grid-cols-3 gap-2">
              <button
                onClick={() => { setActivePanel('context'); setIsMobileMenuOpen(false) }}
                className={`flex flex-col items-center gap-1 p-3 rounded-lg transition-colors ${activePanel === 'context' ? 'bg-primary text-primary-foreground' : 'bg-muted hover:bg-muted/80'}`}
              >
                <Database className="w-5 h-5" />
                <span className="text-xs font-medium">Data</span>
              </button>
              <button
                onClick={() => { setActivePanel('notebook'); setIsMobileMenuOpen(false) }}
                className={`flex flex-col items-center gap-1 p-3 rounded-lg transition-colors ${activePanel === 'notebook' ? 'bg-primary text-primary-foreground' : 'bg-muted hover:bg-muted/80'}`}
              >
                <Code className="w-5 h-5" />
                <span className="text-xs font-medium">Notebook</span>
              </button>
              <button
                onClick={() => { setActivePanel('agent'); setIsMobileMenuOpen(false) }}
                className={`flex flex-col items-center gap-1 p-3 rounded-lg transition-colors ${activePanel === 'agent' ? 'bg-primary text-primary-foreground' : 'bg-muted hover:bg-muted/80'}`}
              >
                <MessageSquare className="w-5 h-5" />
                <span className="text-xs font-medium">Agent</span>
              </button>
            </div>
          )}
        </header>

        {/* Mobile Content */}
        <main className="flex-1 overflow-hidden">
          {activePanel === 'context' && (
            <div className="h-full overflow-auto">
              <DataDeck />
            </div>
          )}
          {activePanel === 'notebook' && currentNotebook && (
            <div className="h-full overflow-auto">
              <InteractiveNotebook />
            </div>
          )}
          {activePanel === 'agent' && (
            <div className="h-full overflow-auto">
              <ChatInterface onGhostCellsGenerated={handleGhostCellsGenerated} />
              <div className="p-4 border-t border-border">
                <InstructionProcessor />
              </div>
            </div>
          )}
        </main>
      </div>
    )
  }

  // Desktop view - three panels
  return (
    <div className="h-screen bg-background">
      <PanelGroup direction="horizontal" className="h-full">
        {/* Left Panel - Context */}
        <Panel defaultSize={25} minSize={20} maxSize={35} className="bg-card">
          <div className="h-full overflow-auto border-r border-border">
            <DataDeck />
          </div>
        </Panel>

        <PanelResizeHandle className="w-2 bg-border hover:bg-primary/30 transition-colors" />

        {/* Center Panel - Notebook */}
        <Panel defaultSize={50} minSize={30}>
          <div className="h-full overflow-auto">
            {currentNotebook ? (
              <InteractiveNotebook />
            ) : (
              <div className="h-full flex items-center justify-center">
                <div className="text-center p-8">
                  <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
                    <Code className="w-8 h-8 text-muted-foreground" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground mb-2">No Notebook</h3>
                  <p className="text-muted-foreground mb-6">Create a notebook to start analyzing your data</p>
                  <InstructionProcessor />
                </div>
              </div>
            )}
          </div>
        </Panel>

        <PanelResizeHandle className="w-2 bg-border hover:bg-primary/30 transition-colors" />

        {/* Right Panel - Agent */}
        <Panel defaultSize={25} minSize={20} maxSize={35} className="bg-card">
          <div className="h-full flex flex-col border-l border-border">
            <div className="flex-1 overflow-hidden">
              <ChatInterface onGhostCellsGenerated={handleGhostCellsGenerated} />
            </div>
            <div className="border-t border-border p-4">
              <InstructionProcessor />
            </div>
          </div>
        </Panel>
      </PanelGroup>
    </div>
  )
}

export default ThreePanelLayout