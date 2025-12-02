import React, { useState, useRef, useEffect } from 'react'
import { useNotebook } from '../../contexts/NotebookContext'
import api from '../../services/api'
import AgentMessage from './AgentMessage'
import { Send, Bot, User, Loader, Sparkles, FileCode } from 'lucide-react'
import toast from 'react-hot-toast'

const ChatInterface = ({ onGhostCellsGenerated }) => {
  const { currentSession, currentNotebook, processInstruction } = useNotebook()
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      content: 'Hello! I\'m your AI data science assistant. I can help you analyze data, create visualizations, clean datasets, and generate insights. How can I assist you today?',
      timestamp: new Date().toISOString(),
      type: 'welcome'
    }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const suggestedPrompts = [
    "Analyze the dataset and provide key insights",
    "Create visualizations for numerical columns",
    "Check data quality and identify issues",
    "Show correlations between variables",
    "Generate time series analysis",
    "Detect and handle outliers"
  ]

  const handleSend = async (e) => {
    e?.preventDefault()

    if (!input.trim() || isLoading) return

    // Check if we have a session and notebook
    if (!currentSession || !currentNotebook) {
      toast.error('Please upload a dataset first')
      return
    }

    const userMessage = {
      id: messages.length + 1,
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    const userInstruction = input
    setInput('')
    setIsLoading(true)

    try {
      // REAL AI CALL - Not mocked!
      const result = await api.processNotebookInstruction(currentNotebook.id, {
        session_id: currentSession.id,
        instruction: userInstruction
      })

      if (result.success && result.proposed_cells && result.proposed_cells.length > 0) {
        // AI generated Ghost Cells!
        const assistantMessage = {
          id: messages.length + 2,
          role: 'assistant',
          content: result.explanation || `I've generated ${result.proposed_cells.length} code cell(s) based on your request. Please review and click "Accept & Run" to execute them.`,
          timestamp: new Date().toISOString(),
          type: 'code_generation',
          ghostCells: result.proposed_cells
        }

        setMessages(prev => [...prev, assistantMessage])

        // Notify parent to add Ghost Cells to notebook
        if (onGhostCellsGenerated) {
          onGhostCellsGenerated(result.proposed_cells)
        }

        toast.success(`AI generated ${result.proposed_cells.length} code suggestions`)
      } else {
        // AI couldn't generate code
        const assistantMessage = {
          id: messages.length + 2,
          role: 'assistant',
          content: result.explanation || "I couldn't generate code for that request. Could you please rephrase or provide more details?",
          timestamp: new Date().toISOString(),
          type: 'response'
        }
        setMessages(prev => [...prev, assistantMessage])
      }

    } catch (error) {
      console.error('Chat error:', error)
      toast.error('Failed to process instruction')

      const errorMessage = {
        id: messages.length + 2,
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString(),
        type: 'error'
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleQuickAction = (action) => {
    setInput(action)
    setTimeout(() => {
      inputRef.current?.focus()
    }, 100)
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border bg-card">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg">
            <Bot className="w-6 h-6 text-primary" />
          </div>
          <div>
            <h2 className="font-semibold text-lg text-foreground">AI Assistant</h2>
            <p className="text-sm text-muted-foreground">
              Expert data science guidance and automation
            </p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto custom-scrollbar p-4 space-y-4">
        {messages.map((message) => (
          <AgentMessage
            key={message.id}
            message={message}
            onAction={(action) => console.log('Action:', action)}
          />
        ))}

        {isLoading && (
          <div className="flex items-center gap-3 p-4 bg-muted/30 rounded-lg">
            <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
              <Bot className="w-4 h-4 text-primary" />
            </div>
            <div className="flex items-center gap-2">
              <Loader className="w-4 h-4 animate-spin text-muted-foreground" />
              <span className="text-muted-foreground">AI is thinking...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompts */}
      {messages.length <= 2 && (
        <div className="px-4 py-3 border-t border-border">
          <p className="text-sm font-medium text-foreground mb-2">Try asking:</p>
          <div className="flex flex-wrap gap-2">
            {suggestedPrompts.map((prompt, index) => (
              <button
                key={index}
                onClick={() => handleQuickAction(prompt)}
                className="text-sm px-3 py-1.5 bg-muted hover:bg-muted/80 rounded-lg transition-colors"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-border bg-card">
        <form onSubmit={handleSend} className="space-y-2">
          <div className="flex gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about your data, request analysis, or give instructions..."
              className="flex-1 p-3 bg-background border border-input rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              rows="2"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="self-end p-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Press Enter to send, Shift+Enter for new line</span>
            <span className="flex items-center gap-1">
              <Sparkles className="w-3 h-3" />
              Powered by GPT-4 & LangChain
            </span>
          </div>
        </form>
      </div>
    </div>
  )
}

export default ChatInterface