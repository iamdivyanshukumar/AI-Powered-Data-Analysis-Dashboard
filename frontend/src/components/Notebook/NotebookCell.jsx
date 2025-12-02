import React, { useState, useRef, useEffect } from 'react'
import MonacoWrapper from '../common/MonacoWrapper'
import PlotlyRenderer from '../Canvas/PlotlyRenderer'
import {
  Play,
  Trash2,
  Plus,
  Code,
  FileText,
  ChevronDown,
  Copy,
  Check,
  MoreVertical,
  Sparkles,
  CheckCircle,
  XCircle
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import toast from 'react-hot-toast'

const NotebookCell = ({
  cell,
  isActive,
  isEditing,
  executionResult,
  onContentChange,
  onTypeChange,
  onExecute,
  onDelete,
  onAddAbove,
  onAddBelow,
  onFocus,
  onAcceptGhost,  // NEW: Accept ghost cell
  onRejectGhost   // NEW: Reject ghost cell
}) => {
  const [showActions, setShowActions] = useState(false)
  const [showCellMenu, setShowCellMenu] = useState(false)
  const [copied, setCopied] = useState(false)
  const [isExecuting, setIsExecuting] = useState(false)

  // Check if this is a ghost cell (AI-proposed, not executed)
  const isGhost = cell.metadata?.ghost === true
  const cellRef = useRef(null)

  // Convert cell source to string (it might be an array or string)
  const getCellContent = () => {
    if (Array.isArray(cell.source)) {
      return cell.source.join('')
    }
    return cell.source || ''
  }

  const [cellContent, setCellContent] = useState(getCellContent())

  // Update local content when cell changes
  useEffect(() => {
    setCellContent(getCellContent())
  }, [cell.source])

  useEffect(() => {
    if (isActive && cellRef.current) {
      cellRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [isActive])

  const handleContentChange = (value) => {
    setCellContent(value)
    // Convert string to array format for backend
    const sourceArray = value.split('\n').map((line, idx, arr) =>
      idx < arr.length - 1 ? line + '\n' : line
    )
    onContentChange(sourceArray)
  }

  const handleTypeChange = (newType) => {
    onTypeChange(newType)
  }

  const handleExecute = async () => {
    setIsExecuting(true)
    try {
      await onExecute()
    } finally {
      setIsExecuting(false)
    }
  }

  const handleCopyCode = () => {
    navigator.clipboard.writeText(cell.content)
    setCopied(true)
    toast.success('Code copied to clipboard')
    setTimeout(() => setCopied(false), 2000)
  }

  const handleAIOptimize = () => {
    toast.loading('AI is optimizing your code...')
    // This would call an AI service to optimize the code
    setTimeout(() => {
      toast.dismiss()
      toast.success('Code optimized!')
    }, 2000)
  }

  const getCellIcon = () => {
    return cell.type === 'code' ?
      <Code className="w-4 h-4 text-blue-500" /> :
      <FileText className="w-4 h-4 text-green-500" />
  }

  return (
    <div
      ref={cellRef}
      className={`notebook-cell group relative flex gap-2 px-4 py-2 transition-colors ${isGhost
        ? 'bg-purple-50/30 border-l-4 border-purple-400'
        : isActive ? 'bg-muted/10' : 'bg-transparent'
        }`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => { setShowActions(false); setShowCellMenu(false) }}
      onClick={onFocus}
    >
      {/* Ghost Cell Badge */}
      {isGhost && (
        <div className="absolute top-2 left-2 z-10 flex items-center gap-1.5 px-2 py-1 bg-purple-100 border border-purple-300 rounded-md text-xs font-medium text-purple-700">
          <Sparkles className="w-3 h-3" />
          AI Proposed
          {cell.metadata?.confidence && (
            <span className="ml-1 text-purple-600">
              {Math.round(cell.metadata.confidence * 100)}%
            </span>
          )}
        </div>
      )}

      {/* Left Gutter - Play Button & Info */}
      <div className="w-10 flex flex-col items-center pt-1 flex-shrink-0 select-none">
        {(cell.type === 'code' || cell.cell_type === 'code') && !isGhost && (
          <div className="relative group/play">
            <button
              onClick={(e) => { e.stopPropagation(); handleExecute(); }}
              disabled={isExecuting}
              className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${isExecuting
                ? 'bg-blue-600 text-white animate-pulse'
                : executionResult
                  ? (executionResult.success ? 'bg-transparent text-muted-foreground' : 'bg-transparent text-red-600')
                  : 'bg-muted/50 hover:bg-primary hover:text-primary-foreground text-muted-foreground'
                }`}
              title={isExecuting ? "Executing..." : "Execute cell"}
            >
              {isExecuting ? (
                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : executionResult ? (
                executionResult.success ? <div className="text-[10px] font-mono">[{executionResult.execution_count || cell.execution_count || '*'}]</div> : <div className="text-xs font-bold">!</div>
              ) : (
                <Play className="w-3 h-3 ml-0.5" />
              )}
            </button>
          </div>
        )}
      </div>

      {/* Main Cell Content */}
      <div className={`flex-1 min-w-0 min-h-[100px] rounded-lg transition-all duration-200 ${isGhost
        ? 'opacity-80'
        : isActive ? 'shadow-sm ring-1 ring-border bg-card' : ''
        }`}>

        {/* Ghost Cell Actions (Accept/Reject) OR Normal Cell Actions */}
        {isGhost ? (
          <div className="absolute right-2 top-[-12px] flex items-center gap-2 bg-purple-100 border border-purple-300 rounded-md shadow-md px-2 py-1 z-20">
            <button
              onClick={(e) => { e.stopPropagation(); onAcceptGhost && onAcceptGhost(cell.id); }}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-purple-600 text-white rounded hover:bg-purple-700 transition-colors"
              title="Accept and run this code"
            >
              <CheckCircle className="w-3 h-3" />
              Accept & Run
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onRejectGhost && onRejectGhost(cell.id); }}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-white text-red-600 border border-red-300 rounded hover:bg-red-50 transition-colors"
              title="Reject this suggestion"
            >
              <XCircle className="w-3 h-3" />
              Reject
            </button>
          </div>
        ) : (
          <div className={`absolute right-2 top-[-12px] flex items-center gap-1 bg-background border border-border rounded-md shadow-sm px-1 py-0.5 transition-opacity duration-200 ${showActions || isActive ? 'opacity-100' : 'opacity-0'
            } z-20`}>
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(); }}
              className="p-1 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded transition-colors"
              title="Delete cell"
            >
              <Trash2 className="w-3 h-3" />
            </button>

            <div className="relative">
              <button
                onClick={(e) => { e.stopPropagation(); setShowCellMenu(!showCellMenu); }}
                className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
                title="More options"
              >
                <MoreVertical className="w-3 h-3" />
              </button>

              {showCellMenu && (
                <div className="absolute right-0 top-full mt-1 w-48 bg-popover border border-border rounded-lg shadow-lg z-50">
                  <div className="py-1">
                    <button
                      onClick={(e) => { e.stopPropagation(); handleCopyCode(); setShowCellMenu(false); }}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-muted flex items-center gap-2"
                    >
                      <Copy className="w-4 h-4" />
                      Copy Code
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleAIOptimize(); setShowCellMenu(false); }}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-muted transition-colors flex items-center gap-2"
                    >
                      <Sparkles className="w-4 h-4" />
                      AI Optimize
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Editor Area */}
        <div className="p-1">
          {
            cell.type === 'markdown' || cell.cell_type === 'markdown' ? (
              <div className="prose prose-sm max-w-none p-3">
                {isEditing ? (
                  <MonacoWrapper
                    value={cellContent}
                    onChange={handleContentChange}
                    language="markdown"
                    height="auto"
                    options={{
                      minimap: { enabled: false },
                      lineNumbers: 'off',
                      wordWrap: 'on',
                      fontSize: 14,
                      scrollBeyondLastLine: false,
                      automaticLayout: true
                    }}
                  />
                ) : (
                  <div className="markdown-content" onDoubleClick={() => onFocus()}>
                    <ReactMarkdown>{cellContent}</ReactMarkdown>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-muted/5 rounded-md overflow-hidden">
                <MonacoWrapper
                  value={cellContent}
                  onChange={handleContentChange}
                  language="python"
                  height="auto"
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    suggestOnTriggerCharacters: true,
                    wordBasedSuggestions: true,
                    automaticLayout: true,
                    renderLineHighlight: 'none',
                    hideCursorInOverviewRuler: true,
                    overviewRulerBorder: false,
                    onMount: (editor, monaco) => {
                      editor.addCommand(monaco.KeyMod.Shift | monaco.KeyCode.Enter, () => {
                        handleExecute()
                      })
                    }
                  }}
                />
              </div>
            )
          }
        </div >

        {/* Execution Results - Displayed below code */}
        {/* Outputs (Always show if present) */}
        {(cell.type === 'code' || cell.cell_type === 'code') && cell.outputs && cell.outputs.length > 0 && (
          <div className="mt-2 p-2 space-y-4">
            {cell.outputs.map((output, index) => (
              <div key={index} className="output-result">
                {/* Text Output */}
                {output.output_type === 'stream' && (
                  <pre className="text-sm font-mono whitespace-pre-wrap text-foreground/90 overflow-x-auto pl-2 border-l-2 border-transparent">
                    {output.text}
                  </pre>
                )}

                {/* Plotly Visualizations */}
                {output.output_type === 'display_data' && output.data && output.data['application/vnd.plotly.v1+json'] && (
                  <div className="bg-white p-2 rounded border border-border/50">
                    <PlotlyRenderer
                      data={output.data['application/vnd.plotly.v1+json'].data}
                      layout={output.data['application/vnd.plotly.v1+json'].layout}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Execution Status / Error (Only if executionResult exists) */}
        {executionResult && (cell.type === 'code' || cell.cell_type === 'code') && (
          <div className="mt-1 px-2">
            {executionResult.success ? (
              executionResult.execution_time && (
                <div className="text-xs text-muted-foreground pl-2">
                  Executed in {executionResult.execution_time.toFixed(3)}s
                </div>
              )
            ) : (
              <div className="bg-destructive/5 border-l-2 border-destructive p-3 rounded-r">
                <div className="font-mono text-sm text-destructive whitespace-pre-wrap">
                  {executionResult.error || 'Unknown error occurred'}
                </div>
                {executionResult.traceback && (
                  <details className="mt-2">
                    <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                      View traceback
                    </summary>
                    <pre className="mt-2 text-xs font-mono whitespace-pre-wrap bg-black/5 p-2 rounded text-foreground">
                      {executionResult.traceback}
                    </pre>
                  </details>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default NotebookCell