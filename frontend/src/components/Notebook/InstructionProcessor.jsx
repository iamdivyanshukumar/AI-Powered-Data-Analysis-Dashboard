import React, { useState } from 'react'
import { useNotebook } from '../../contexts/NotebookContext'
import { Wand2, Send, Sparkles, Zap, Brain, TrendingUp } from 'lucide-react'
import toast from 'react-hot-toast'

const InstructionProcessor = () => {
  const { processInstruction, currentSession } = useNotebook()
  const [instruction, setInstruction] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)

  const suggestedInstructions = [
    {
      icon: <Sparkles className="w-4 h-4" />,
      text: "Create comprehensive EDA notebook",
      description: "Generate full exploratory analysis"
    },
    {
      icon: <Zap className="w-4 h-4" />,
      text: "Remove outliers from numerical columns",
      description: "Clean data using IQR method"
    },
    {
      icon: <Brain className="w-4 h-4" />,
      text: "Handle missing values",
      description: "Smart imputation strategy"
    },
    {
      icon: <TrendingUp className="w-4 h-4" />,
      text: "Analyze correlations",
      description: "Find relationships between variables"
    }
  ]

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!instruction.trim()) {
      toast.error('Please enter an instruction')
      return
    }

    if (!currentSession) {
      toast.error('Please upload a dataset first')
      return
    }

    setIsProcessing(true)
    try {
      await processInstruction(instruction)
      setInstruction('') // Clear input after success
    } catch (error) {
      console.error('Instruction processing error:', error)
    } finally {
      setIsProcessing(false)
    }
  }

  const handleQuickInstruction = (instructionText) => {
    setInstruction(instructionText)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <div className="p-2 bg-primary/10 rounded-lg">
          <Wand2 className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h3 className="font-semibold text-foreground">AI Assistant</h3>
          <p className="text-sm text-muted-foreground">Tell me what to do with your data</p>
        </div>
      </div>

      {/* Instruction Input */}
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="relative">
          <textarea
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            placeholder="Describe what you want to do with your data (e.g., 'Clean the data', 'Create visualizations', 'Analyze trends')"
            className="w-full p-3 pr-10 bg-background border border-input rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent resize-none transition-colors"
            rows="3"
            disabled={isProcessing}
          />
          <button
            type="submit"
            disabled={!instruction.trim() || isProcessing || !currentSession}
            className="absolute bottom-3 right-3 p-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Execute instruction"
          >
            {isProcessing ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>

        {!currentSession && (
          <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm text-yellow-800">
              Please upload a dataset to use AI instructions
            </p>
          </div>
        )}
      </form>

      {/* Suggested Instructions */}
      <div>
        <p className="text-sm font-medium text-foreground mb-2">Quick Actions</p>
        <div className="grid grid-cols-2 gap-2">
          {suggestedInstructions.map((suggestion, index) => (
            <button
              key={index}
              onClick={() => handleQuickInstruction(suggestion.text)}
              disabled={!currentSession}
              className="group text-left p-3 bg-card border border-border rounded-lg hover:border-primary hover:bg-primary/5 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              <div className="flex items-start gap-2">
                <div className="p-1.5 bg-primary/10 rounded group-hover:bg-primary/20 transition-colors">
                  {suggestion.icon}
                </div>
                <div>
                  <div className="font-medium text-sm text-foreground">
                    {suggestion.text}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {suggestion.description}
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Examples */}
      <div className="p-3 bg-muted/30 rounded-lg">
        <p className="text-sm font-medium text-foreground mb-2">Examples</p>
        <div className="space-y-1 text-sm">
          <code className="block px-2 py-1 bg-background rounded text-xs">
            "Create a correlation heatmap"
          </code>
          <code className="block px-2 py-1 bg-background rounded text-xs">
            "Remove outliers using z-score method"
          </code>
          <code className="block px-2 py-1 bg-background rounded text-xs">
            "Generate time series analysis"
          </code>
          <code className="block px-2 py-1 bg-background rounded text-xs">
            "Build machine learning model to predict sales"
          </code>
        </div>
      </div>
    </div>
  )
}

export default InstructionProcessor