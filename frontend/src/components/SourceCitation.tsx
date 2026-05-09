import React from 'react'
import { motion } from 'framer-motion'
import { ExternalLink, Calendar } from 'lucide-react'

interface SourceCitationProps {
  source: string
  lastUpdated?: string
}

export default function SourceCitation({ source, lastUpdated }: SourceCitationProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="source-card mt-3"
    >
      <div className="flex items-start gap-2">
        <ExternalLink className="w-4 h-4 text-accent mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-text-muted">Source</span>
            <a
              href={source}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-accent hover:text-accent-hover transition-colors truncate max-w-[200px]"
            >
              {source}
            </a>
          </div>
          {lastUpdated && (
            <div className="flex items-center gap-1">
              <Calendar className="w-3 h-3 text-text-muted" />
              <span className="text-xs text-text-muted">
                {lastUpdated}
              </span>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
