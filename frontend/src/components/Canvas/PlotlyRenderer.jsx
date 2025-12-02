import React from 'react'
import Plot from 'react-plotly.js'

const PlotlyRenderer = ({ data, layout, config }) => {
  const defaultLayout = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'Inter, sans-serif', size: 12, color: '#374151' },
    margin: { l: 60, r: 30, t: 40, b: 50 },
    hovermode: 'closest',
    showlegend: true,
    legend: {
      orientation: 'h',
      yanchor: 'bottom',
      y: 1.02,
      xanchor: 'right',
      x: 1
    },
    ...layout
  }

  const defaultConfig = {
    displayModeBar: true,
    responsive: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['sendDataToCloud', 'select2d', 'lasso2d'],
    ...config
  }

  if (!data) {
    return (
      <div className="h-64 flex items-center justify-center bg-muted/30 rounded-lg">
        <div className="text-center text-muted-foreground">
          <div className="w-12 h-12 border-2 border-dashed border-border rounded-lg mx-auto mb-3"></div>
          <p>No visualization data available</p>
        </div>
      </div>
    )
  }

  return (
    <div className="plotly-renderer">
      <Plot
        data={Array.isArray(data) ? data : [data]}
        layout={defaultLayout}
        config={defaultConfig}
        style={{ width: '100%', height: '400px' }}
        useResizeHandler={true}
      />
    </div>
  )
}

export default PlotlyRenderer