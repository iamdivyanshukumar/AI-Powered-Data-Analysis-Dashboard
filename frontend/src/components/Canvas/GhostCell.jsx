import React, { useState } from 'react'
import MonacoWrapper from '../common/MonacoWrapper'
import { Play, Code, ChartBar, Loader, Sparkles } from 'lucide-react'

const GhostCell = ({ cell, onExecute, onUpdate }) => {
  const [isExecuting, setIsExecuting] = useState(false)
  const [showCode, setShowCode] = useState(true)
  const [code, setCode] = useState(cell?.code || '')
  const [result, setResult] = useState(cell?.result)

  const handleExecute = async () => {
    if (!code.trim()) return
    
    setIsExecuting(true)
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      // Mock result for demo
      const mockResult = {
        success: true,
        outputs: [
          {
            type: 'plot',
            format: 'plotly',
            data: {
              data: [{ x: [1, 2, 3], y: [2, 3, 1], type: 'scatter', mode: 'lines+markers' }],
              layout: { title: 'Sample Plot' }
            }
          }
        ],
        variables_created: ['df_clean', 'correlation_matrix'],
        execution_time: 1.23
      }
      
      setResult(mockResult)
      onUpdate?.({ ...cell, code, result: mockResult })
    } catch (error) {
      console.error('Execution error:', error)
    } finally {
      setIsExecuting(false)
    }
  }

  const handleCodeChange = (value) => {
    setCode(value)
    onUpdate?.({ ...cell, code: value })
  }

  const handleAISuggest = () => {
    const suggestions = [
      '# Try visualizing the data\nimport plotly.express as px\nfig = px.scatter(df, x=\'column1\', y=\'column2\')\nfig.show()',
      '# Basic statistics\nprint(df.describe())\nprint(df.info())',
      '# Handle missing values\ndf_clean = df.dropna()\nprint(f"Removed {len(df) - len(df_clean)} rows")'
    ]
    const randomSuggestion = suggestions[Math.floor(Math.random() * suggestions.length)]
    setCode(randomSuggestion)
  }

  return (
    <div className="border border-dashed border-primary/30 rounded-lg bg-background hover:border-primary/50 transition-colors mb-4">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-primary/10 rounded">
            <Sparkles className="w-4 h-4 text-primary" />
          </div>
          <span className="text-sm font-medium text-foreground">AI-Generated Analysis</span>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCode(!showCode)}
            className="p-1.5 hover:bg-muted rounded transition-colors"
            title={showCode ? 'Hide code' : 'Show code'}
          >
            <Code className="w-4 h-4" />
          </button>
          
          <button
            onClick={handleAISuggest}
            className="p-1.5 text-purple-600 hover:bg-purple-100 rounded transition-colors"
            title="AI Suggestions"
          >
            <Sparkles className="w-4 h-4" />
          </button>
          
          <button
            onClick={handleExecute}
            disabled={isExecuting || !code.trim()}
            className="flex items-center gap-1 px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isExecuting ? (
              <Loader className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            Run
          </button>
        </div>
      </div>

      {/* Code Editor */}
      {showCode && (
        <div className="border-b border-border">
          <MonacoWrapper
            value={code}
            onChange={handleCodeChange}
            language="python"
            height="200px"
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
            }}
          />
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="p-4">
          {result.success && (
            <>
              {result.outputs?.map((viz, index) => (
                <div key={index} className="mb-4 p-3 bg-white rounded border">
                  <div className="text-sm text-muted-foreground mb-2">Visualization {index + 1}</div>
                  <div className="h-48 flex items-center justify-center bg-gray-50 rounded">
                    <ChartBar className="w-12 h-12 text-gray-400" />
                  </div>
                </div>
              ))}
              
              {result.variables_created && result.variables_created.length > 0 && (
                <div className="mt-4 p-3 bg-muted rounded-lg">
                  <h4 className="font-medium mb-2">Variables Created:</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    {result.variables_created.map((variable, idx) => (
                      <div key={idx} className="flex justify-between">
                        <code className="text-primary">{variable}</code>
                        <span className="text-muted-foreground">Ready</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
          
          {!result.success && (
            <div className="p-3 bg-destructive/10 border border-destructive/20 rounded">
              <div className="text-destructive text-sm">
                Execution failed: {result.error || 'Unknown error'}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default GhostCell