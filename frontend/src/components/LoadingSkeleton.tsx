import React from 'react'
import { motion } from 'framer-motion'

export default function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      {/* Message Skeleton */}
      <div className="flex gap-3">
        <div className="skeleton w-8 h-8 rounded-full" />
        <div className="flex-1 space-y-2">
          <div className="skeleton h-4 w-3/4 rounded" />
          <div className="skeleton h-3 w-full rounded" />
        </div>
      </div>

      {/* Response Skeleton */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="flex gap-3"
      >
        <div className="skeleton w-8 h-8 rounded-full" />
        <div className="flex-1 space-y-3">
          <div className="skeleton h-4 w-2/3 rounded" />
          <div className="skeleton h-3 w-full rounded" />
          <div className="skeleton h-4 w-1/2 rounded" />
          <div className="skeleton h-3 w-1/3 rounded" />
        </div>
      </motion.div>

      {/* Input Skeleton */}
      <div className="flex gap-3 pt-4">
        <div className="skeleton h-12 flex-1 rounded" />
        <div className="skeleton w-10 h-10 rounded" />
      </div>
    </div>
  )
}
