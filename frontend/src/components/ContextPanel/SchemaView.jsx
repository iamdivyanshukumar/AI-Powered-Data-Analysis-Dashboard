import React, { useState } from 'react'
import { useNotebook } from '../../contexts/NotebookContext'
import { ChevronDown, ChevronRight, Hash, Type, Calendar, Percent, DollarSign, Clock } from 'lucide-react'

const SchemaView = () => {
  const { currentSession } = useNotebook()
  const [expandedColumns, setExpandedColumns] = useState({})

  if (!currentSession?.dataframe?.columns) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        No schema data available
      </div>
    )
  }

  const { dataframe } = currentSession
  const columns = dataframe.columns || []

  const toggleColumn = (columnName) => {
    setExpandedColumns(prev => ({
      ...prev,
      [columnName]: !prev[columnName]
    }))
  }

  const getColumnIcon = (dtype, columnName) => {
    if (dtype === 'number') {
      if (columnName.toLowerCase().includes('percent') || columnName.toLowerCase().includes('rate')) {
        return <Percent className="w-4 h-4 text-blue-500" />
      }
      if (columnName.toLowerCase().includes('price') || columnName.toLowerCase().includes('cost') || columnName.toLowerCase().includes('amount')) {
        return <DollarSign className="w-4 h-4 text-green-500" />
      }
      return <Hash className="w-4 h-4 text-blue-500" />
    }
    if (['object', 'string'].includes(dtype)) {
      return <Type className="w-4 h-4 text-green-500" />
    }
    if (dtype.includes('date') || dtype.includes('time')) {
      return columnName.toLowerCase().includes('date') ? 
        <Calendar className="w-4 h-4 text-orange-500" /> : 
        <Clock className="w-4 h-4 text-purple-500" />
    }
    return <Type className="w-4 h-4 text-gray-500" />
  }

  const getColumnStats = (columnName) => {
    const sample = dataframe.sample_data?.[0]?.[columnName]
    const dtype = dataframe.dtypes?.[columnName] || 'unknown'
    
    const stats = dataframe.column_stats?.[columnName] || {}
    
    return {
      sample,
      dtype,
      unique: stats.unique_count || 'N/A',
      missing: stats.missing_percentage ? `${stats.missing_percentage}%` : 'N/A',
      stats: stats
    }
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-foreground">Dataset Schema</h3>
        <span className="text-sm text-muted-foreground">
          {columns.length} columns
        </span>
      </div>

      <div className="space-y-2">
        {columns.map((column) => {
          const stats = getColumnStats(column)
          const isExpanded = expandedColumns[column]
          
          return (
            <div key={column} className="border rounded-lg overflow-hidden bg-card hover:border-border/80 transition-colors">
              <button
                onClick={() => toggleColumn(column)}
                className="w-full p-3 text-left flex items-center justify-between hover:bg-muted/30 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {getColumnIcon(stats.dtype, column)}
                  <div className="text-left">
                    <div className="font-medium text-sm text-foreground">{column}</div>
                    <div className="text-xs text-muted-foreground capitalize">
                      {stats.dtype}
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  {stats.unique !== 'N/A' && (
                    <span className="text-xs px-2 py-1 bg-muted rounded">
                      {stats.unique} unique
                    </span>
                  )}
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-muted-foreground" />
                  )}
                </div>
              </button>
              
              {isExpanded && (
                <div className="p-3 border-t bg-muted/20 space-y-3">
                  {/* Sample Value */}
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Sample Value</div>
                    <code className="block px-3 py-2 bg-background border rounded text-sm font-mono">
                      {stats.sample !== undefined ? String(stats.sample) : 'N/A'}
                    </code>
                  </div>

                  {/* Statistics */}
                  {stats.stats && Object.keys(stats.stats).length > 0 && (
                    <div>
                      <div className="text-xs text-muted-foreground mb-1">Statistics</div>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        {stats.stats.min !== undefined && (
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Min:</span>
                            <span className="font-medium">{stats.stats.min.toFixed(2)}</span>
                          </div>
                        )}
                        {stats.stats.max !== undefined && (
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Max:</span>
                            <span className="font-medium">{stats.stats.max.toFixed(2)}</span>
                          </div>
                        )}
                        {stats.stats.mean !== undefined && (
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Mean:</span>
                            <span className="font-medium">{stats.stats.mean.toFixed(2)}</span>
                          </div>
                        )}
                        {stats.stats.std !== undefined && (
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Std Dev:</span>
                            <span className="font-medium">{stats.stats.std.toFixed(2)}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Missing Values */}
                  {stats.missing !== 'N/A' && stats.missing !== '0%' && (
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Missing Values:</span>
                      <span className={`font-medium ${parseFloat(stats.missing) > 10 ? 'text-destructive' : 'text-warning'}`}>
                        {stats.missing}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default SchemaView