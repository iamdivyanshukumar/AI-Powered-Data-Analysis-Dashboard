import React, { useState } from 'react'
import {
  Save,
  Play,
  Sparkles,
  Edit3,
  Eye,
  Download,
  Trash2,
  Settings,
  Share2,
  ChevronDown
} from 'lucide-react'
import toast from 'react-hot-toast'

const NotebookToolbar = ({
  notebook,
  onExport,
  onToggleEdit,
  isEditing,
  showExecutionPanel,
  onToggleExecutionPanel,
  onRunAll,
  onAIGenerate,
  onClearOutputs
}) => {
  const [showExportMenu, setShowExportMenu] = useState(false)

  const handleSave = () => {
    toast.success('Notebook saved')
  }

  const handleRunAll = () => {
    if (onRunAll) {
      onRunAll()
    } else {
      toast.success('Running all cells...')
    }
  }

  const handleAIGenerate = () => {
    if (onAIGenerate) {
      onAIGenerate()
    } else {
      toast.loading('AI is generating analysis...')
      setTimeout(() => {
        toast.dismiss()
        toast.success('AI analysis complete')
      }, 2000)
    }
  }

  const handleClearOutputs = () => {
    if (onClearOutputs) {
      onClearOutputs()
    } else {
      toast.success('Outputs cleared')
    }
  }

  const handleExport = (format) => {
    if (onExport) {
      onExport(format)
    }
    setShowExportMenu(false)
    toast.success(`Exported as ${format} `)
  }

  return (
    <div className="border-b border-border bg-background">
      <div className="px-4 py-2.5 flex items-center justify-between">
        {/* Left: Title */}
        <div className="flex items-center gap-3">
          <h2 className="font-semibold text-lg text-foreground">
            {notebook?.title || 'Exploratory Data Analysis'}
          </h2>
          <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
            .ipynb
          </span>
        </div>

        {/* Center: Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleSave}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-muted text-foreground rounded-md hover:bg-muted/80 transition-colors"
          >
            <Save className="w-4 h-4" />
            Save
          </button>

          <button
            onClick={handleRunAll}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
          >
            <Play className="w-4 h-4" />
            Run All
          </button>

          <button
            onClick={handleAIGenerate}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors"
          >
            <Sparkles className="w-4 h-4" />
            AI Generate
          </button>

          <button
            onClick={onToggleEdit}
            className={`flex items - center gap - 1.5 px - 3 py - 1.5 text - sm font - medium rounded - md transition - colors ${isEditing
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-muted text-foreground hover:bg-muted/80'
              } `}
          >
            {isEditing ? <Eye className="w-4 h-4" /> : <Edit3 className="w-4 h-4" />}
            {isEditing ? 'Preview' : 'Edit'}
          </button>
        </div>

        {/* Right: Utility Buttons */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium bg-muted text-foreground rounded-md hover:bg-muted/80 transition-colors"
            >
              <Download className="w-4 h-4" />
              Export
              <ChevronDown className="w-3 h-3" />
            </button>

            {showExportMenu && (
              <div className="absolute right-0 top-full mt-1 w-48 bg-popover border border-border rounded-lg shadow-lg z-50">
                <div className="py-1">
                  <button onClick={() => handleExport('ipynb')} className="w-full text-left px-3 py-2 text-sm hover:bg-muted transition-colors">
                    Jupyter Notebook (.ipynb)
                  </button>
                  <button onClick={() => handleExport('html')} className="w-full text-left px-3 py-2 text-sm hover:bg-muted transition-colors">
                    HTML (.html)
                  </button>
                  <button onClick={() => handleExport('pdf')} className="w-full text-left px-3 py-2 text-sm hover:bg-muted transition-colors">
                    PDF (.pdf)
                  </button>
                  <button onClick={() => handleExport('py')} className="w-full text-left px-3 py-2 text-sm hover:bg-muted transition-colors">
                    Python Script (.py)
                  </button>
                </div>
              </div>
            )}
          </div>

          <button
            onClick={handleClearOutputs}
            className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium bg-muted text-foreground rounded-md hover:bg-muted/80 transition-colors"
            title="Clear all outputs"
          >
            <Trash2 className="w-4 h-4" />
            Clear Outputs
          </button>

          <button
            onClick={onToggleExecutionPanel}
            className={`p - 1.5 rounded - md transition - colors ${showExecutionPanel
                ? 'bg-primary/10 text-primary'
                : 'text-muted-foreground hover:bg-muted'
              } `}
            title="Toggle Execution Panel"
          >
            <Settings className="w-4 h-4" />
          </button>

          <button
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            <Share2 className="w-4 h-4" />
            Share
          </button>
        </div>
      </div>
    </div>
  )
}

export default NotebookToolbar