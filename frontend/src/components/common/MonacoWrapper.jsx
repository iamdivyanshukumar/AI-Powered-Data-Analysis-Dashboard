import React, { useState, useEffect } from 'react'
import Editor from '@monaco-editor/react'

const MonacoWrapper = ({ value, onChange, language, height, options = {}, theme = "vs-dark" }) => {
  const [editorHeight, setEditorHeight] = useState(height)

  // Calculate height based on content if height is "auto"
  useEffect(() => {
    if (height === 'auto' && value) {
      const lineCount = value.split('\n').length
      const calculatedHeight = Math.max(100, Math.min(lineCount * 20 + 10, 600))
      setEditorHeight(`${calculatedHeight}px`)
    } else if (height !== 'auto') {
      setEditorHeight(height)
    }
  }, [value, height])

  const defaultOptions = {
    minimap: { enabled: false },
    fontSize: 14,
    scrollBeyondLastLine: false,
    wordWrap: 'on',
    automaticLayout: true,
    formatOnPaste: true,
    formatOnType: true,
    suggestOnTriggerCharacters: true,
    acceptSuggestionOnEnter: 'on',
    snippetSuggestions: 'inline',
    ...options
  }

  const handleEditorWillMount = (monaco) => {
    // Register custom themes
    monaco.editor.defineTheme('autovizai', {
      base: 'vs-dark',
      inherit: true,
      rules: [
        { token: 'comment', foreground: '6A9955' },
        { token: 'keyword', foreground: '569CD6' },
        { token: 'string', foreground: 'CE9178' },
        { token: 'number', foreground: 'B5CEA8' },
      ],
      colors: {
        'editor.background': '#1E1E1E',
        'editor.lineHighlightBackground': '#2A2D2E',
        'editorCursor.foreground': '#AEAFAD',
        'editor.selectionBackground': '#264F78',
      }
    })
  }

  return (
    <div className="monaco-wrapper" style={{ minHeight: '100px' }}>
      <Editor
        height={editorHeight || '200px'}
        language={language}
        value={value}
        theme="autovizai"
        onChange={onChange}
        options={defaultOptions}
        onMount={options.onMount}
        beforeMount={handleEditorWillMount}
        loading={
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        }
      />
    </div>
  )
}

export default MonacoWrapper