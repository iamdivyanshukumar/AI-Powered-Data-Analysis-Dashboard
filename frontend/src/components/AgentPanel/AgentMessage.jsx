import React from 'react'
import ReactMarkdown from 'react-markdown'
import { Bot, User, FileCode, Sparkles, BarChart3, Download, CheckCircle } from 'lucide-react'

const AgentMessage = ({ message, onAction }) => {
  const isAssistant = message.role === 'assistant'
  const timestamp = new Date(message.timestamp).toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit' 
  })

  const renderContent = () => {
    if (message.type === 'code') {
      return (
        <div className="space-y-3">
          <ReactMarkdown>{message.content}</ReactMarkdown>
          {message.code && (
            <pre className="bg-black/5 p-3 rounded-lg overflow-x-auto text-sm">
              <code>{message.code}</code>
            </pre>
          )}
        </div>
      )
    }

    if (message.type === 'analysis') {
      return (
        <div className="space-y-3">
          <ReactMarkdown>{message.content}</ReactMarkdown>
          {message.insights && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-blue-500" />
                <span className="font-medium text-blue-800">Key Insights</span>
              </div>
              <ul className="space-y-1 text-sm text-blue-700">
                {message.insights.map((insight, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    {insight}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )
    }

    return <ReactMarkdown>{message.content}</ReactMarkdown>
  }

  return (
    <div className={`flex gap-3 ${isAssistant ? '' : 'flex-row-reverse'}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isAssistant ? 'bg-primary/10' : 'bg-secondary/10'
      }`}>
        {isAssistant ? (
          <Bot className="w-4 h-4 text-primary" />
        ) : (
          <User className="w-4 h-4 text-secondary" />
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 max-w-[85%] ${isAssistant ? '' : 'text-right'}`}>
        <div className={`rounded-lg p-3 ${
          isAssistant 
            ? 'bg-card border border-border' 
            : 'bg-primary text-primary-foreground'
        }`}>
          {renderContent()}
          
          {/* Actions */}
          {isAssistant && message.actions && (
            <div className="mt-3 pt-3 border-t border-border flex flex-wrap gap-2">
              {message.actions.map((action, idx) => (
                <button
                  key={idx}
                  onClick={() => onAction?.(action.action)}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm bg-muted hover:bg-muted/80 rounded-lg transition-colors"
                >
                  {action.icon && <action.icon className="w-3 h-3" />}
                  {action.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Timestamp */}
        <div className={`mt-1 text-xs text-muted-foreground ${isAssistant ? '' : 'text-right'}`}>
          {timestamp}
          {message.type && (
            <span className="ml-2 px-1.5 py-0.5 bg-muted rounded">
              {message.type}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export default AgentMessage