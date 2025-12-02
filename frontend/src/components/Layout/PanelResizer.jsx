import React from 'react'

const PanelResizer = ({ onResize, side = 'right' }) => {
  const handleMouseDown = (e) => {
    e.preventDefault()
    const startX = e.clientX
    const startWidth = side === 'right' ? 
      e.target.previousElementSibling.offsetWidth : 
      e.target.nextElementSibling.offsetWidth
    
    const handleMouseMove = (moveEvent) => {
      const delta = moveEvent.clientX - startX
      const newWidth = startWidth + delta
      onResize(Math.max(200, Math.min(600, newWidth)))
    }

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    document.body.style.cursor = 'col-resize'
  }

  return (
    <div
      className={`w-2 h-full cursor-col-resize bg-border hover:bg-primary/30 transition-colors ${
        side === 'right' ? 'border-r' : 'border-l'
      }`}
      onMouseDown={handleMouseDown}
    />
  )
}

export default PanelResizer