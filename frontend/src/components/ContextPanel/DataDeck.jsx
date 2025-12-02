import React, { useState } from 'react'
import { useNotebook } from '../../contexts/NotebookContext'
import SchemaView from './SchemaView'
import VariablesPanel from './VariablesPanel'
import UploadZone from '../common/UploadZone' // <--- IMPORT ADDED
import { Database, Table, Hash, Type, Info, BarChart3, Download, PlusCircle } from 'lucide-react'
import toast from 'react-hot-toast'

const DataDeck = () => {
  const { currentSession, clearSession } = useNotebook()
  const [activeTab, setActiveTab] = useState('schema')

  // --- EMPTY STATE (NotebookLM Style) ---
  if (!currentSession || !currentSession.dataframe) {
    return (
      <div className="h-full flex flex-col p-6">
        {/* Header Title */}
        <div className="flex items-center gap-2 mb-8">
          <Database className="w-5 h-5 text-primary" />
          <h2 className="font-semibold text-lg tracking-tight">Data Deck</h2>
        </div>

        {/* THE MAGIC: 
           We wrap the "No Dataset" design in UploadZone.
           Now the whole design is a clickable dropzone.
        */}
        <div className="flex-1 flex flex-col items-center justify-center -mt-20">
          <UploadZone className="w-full max-w-sm">
            <div className="
              group
              flex flex-col items-center justify-center 
              p-8 rounded-2xl 
              border border-dashed border-transparent
              hover:bg-muted/40 hover:border-border 
              transition-all duration-300 ease-in-out
            ">
              <div className="
                w-16 h-16 bg-muted/50 rounded-full 
                flex items-center justify-center mb-5
                group-hover:scale-110 group-hover:bg-primary/10
                transition-all duration-300
              ">
                <PlusCircle className="w-8 h-8 text-muted-foreground group-hover:text-primary transition-colors" />
              </div>

              <h3 className="text-lg font-semibold text-foreground mb-2">
                No Dataset Loaded
              </h3>

              <p className="text-muted-foreground text-center text-sm max-w-[240px]">
                Click here to upload a CSV file<br />or drag and drop it directly.
              </p>
            </div>
          </UploadZone>
        </div>
      </div>
    )
  }

  // --- ACTIVE STATE (Standard View) ---
  const { dataframe, filename } = currentSession

  const numericCols = dataframe.columns?.filter(col =>
    dataframe.dtypes?.[col] === 'number' ||
    dataframe.dtypes?.[col] === 'int64' ||
    dataframe.dtypes?.[col] === 'float64'
  ) || []

  const categoricalCols = dataframe.columns?.filter(col =>
    ['object', 'string', 'bool'].includes(dataframe.dtypes?.[col])
  ) || []

  const handleDownloadDataset = () => {
    if (dataframe?.sample_data) {
      const csvContent = convertToCSV(dataframe.sample_data)
      const blob = new Blob([csvContent], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `dataset-${filename || 'export'}.csv`
      a.click()
      toast.success('Dataset downloaded')
    }
  }

  const convertToCSV = (data) => {
    if (!data || data.length === 0) return ''
    const headers = Object.keys(data[0])
    const rows = data.map(row =>
      headers.map(header => JSON.stringify(row[header])).join(',')
    )
    return [headers.join(','), ...rows].join('\n')
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border bg-card">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Database className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h2 className="font-semibold text-foreground">Data Deck</h2>
              <p className="text-sm text-muted-foreground truncate max-w-[200px]">
                {filename || 'Untitled Dataset'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={handleDownloadDataset}
              className="p-2 hover:bg-muted rounded-lg transition-colors"
              title="Download dataset"
            >
              <Download className="w-4 h-4 text-muted-foreground" />
            </button>
            <button
              onClick={clearSession}
              className="text-xs px-3 py-1 bg-destructive/10 text-destructive rounded-lg hover:bg-destructive/20 transition-colors"
            >
              Clear
            </button>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex items-center gap-2 p-2 bg-muted/50 rounded-lg">
            <Table className="w-4 h-4 text-blue-500" />
            <div>
              <div className="font-medium">{dataframe.shape?.[0]?.toLocaleString() || 0}</div>
              <div className="text-xs text-muted-foreground">Rows</div>
            </div>
          </div>
          <div className="flex items-center gap-2 p-2 bg-muted/50 rounded-lg">
            <Hash className="w-4 h-4 text-green-500" />
            <div>
              <div className="font-medium">{dataframe.shape?.[1] || 0}</div>
              <div className="text-xs text-muted-foreground">Columns</div>
            </div>
          </div>
          <div className="flex items-center gap-2 p-2 bg-muted/50 rounded-lg">
            <BarChart3 className="w-4 h-4 text-purple-500" />
            <div>
              <div className="font-medium">{numericCols.length}</div>
              <div className="text-xs text-muted-foreground">Numeric</div>
            </div>
          </div>
          <div className="flex items-center gap-2 p-2 bg-muted/50 rounded-lg">
            <Type className="w-4 h-4 text-orange-500" />
            <div>
              <div className="font-medium">{categoricalCols.length}</div>
              <div className="text-xs text-muted-foreground">Categorical</div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-border">
        <div className="flex">
          <button
            onClick={() => setActiveTab('schema')}
            className={`flex-1 py-3 text-sm font-medium transition-colors ${activeTab === 'schema' ? 'text-primary border-b-2 border-primary' : 'text-muted-foreground hover:text-foreground'}`}
          >
            <div className="flex items-center justify-center gap-2">
              <Table className="w-4 h-4" />
              Schema
            </div>
          </button>
          <button
            onClick={() => setActiveTab('variables')}
            className={`flex-1 py-3 text-sm font-medium transition-colors ${activeTab === 'variables' ? 'text-primary border-b-2 border-primary' : 'text-muted-foreground hover:text-foreground'}`}
          >
            <div className="flex items-center justify-center gap-2">
              <Info className="w-4 h-4" />
              Variables
            </div>
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {activeTab === 'schema' ? (
          <SchemaView />
        ) : (
          <VariablesPanel />
        )}
      </div>
    </div>
  )
}

export default DataDeck