import React from 'react'
import { useNotebook } from '../../contexts/NotebookContext'
import ThreePanelLayout from '../Layout/ThreePanelLayout'
import LoadingSpinner from '../common/LoadingSpinner'

const Dashboard = () => {
  const { isLoading } = useNotebook()

  if (isLoading) {
    return <LoadingSpinner message="Loading your workspace..." />
  }

  // Always show 3-panel layout
  // DataDeck handles upload functionality when no session exists
  return <ThreePanelLayout />
}

export default Dashboard