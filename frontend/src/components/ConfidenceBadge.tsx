import React from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, AlertTriangle } from 'lucide-react'

interface ConfidenceBadgeProps {
  confidence: number
}

export default function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  const getConfidenceLevel = () => {
    if (confidence >= 0.7) return 'high'
    if (confidence >= 0.4) return 'medium'
    return 'low'
  }

  const getConfidenceColor = () => {
    if (confidence >= 0.7) return 'confidence-high'
    if (confidence >= 0.4) return 'confidence-medium'
    return 'confidence-low'
  }

  const getConfidenceIcon = () => {
    if (confidence >= 0.7) return TrendingUp
    return AlertTriangle
  }

  const level = getConfidenceLevel()
  const color = getConfidenceColor()
  const Icon = getConfidenceIcon()

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
      className={`inline-flex items-center gap-2 ${color}`}
    >
      <Icon className="w-3 h-3" />
      <span className="text-xs font-medium">
        {Math.round(confidence * 100)}% confidence
      </span>
    </motion.div>
  )
}
