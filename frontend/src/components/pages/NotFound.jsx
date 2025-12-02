import React from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, Home } from 'lucide-react'

const NotFound = () => {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background p-4">
      <div className="text-center max-w-md">
        <div className="p-4 bg-destructive/10 rounded-full w-24 h-24 flex items-center justify-center mx-auto mb-6">
          <AlertTriangle className="w-12 h-12 text-destructive" />
        </div>
        
        <h1 className="text-6xl font-bold text-foreground mb-4">404</h1>
        <h2 className="text-2xl font-semibold text-foreground mb-4">Page Not Found</h2>
        
        <p className="text-muted-foreground mb-8">
          The page you're looking for doesn't exist or has been moved. 
          Let's get you back to familiar territory.
        </p>
        
        <div className="space-y-4">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors"
          >
            <Home className="w-5 h-5" />
            Back to Dashboard
          </Link>
          
          <p className="text-sm text-muted-foreground">
            Having trouble?{' '}
            <Link to="/login" className="text-primary hover:text-primary/80 transition-colors">
              Try logging in again
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

export default NotFound