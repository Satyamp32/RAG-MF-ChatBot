import React from 'react'
import { motion } from 'framer-motion'

export default function LoadingDots() {
  return (
    <div className="flex space-x-1">
      {[0, 1, 2].map((index) => (
        <motion.div
          key={index}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{
            duration: 0.5,
            delay: index * 0.1,
            repeat: Infinity,
            repeatType: 'reverse'
          }}
          className="w-2 h-2 bg-accent rounded-full"
        />
      ))}
    </div>
  )
}
