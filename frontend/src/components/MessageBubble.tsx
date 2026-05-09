import React from 'react'
import { motion } from 'framer-motion'
import { Message } from '@/types/chat'

interface MessageBubbleProps {
  message: Message
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
      className={message.role === 'user' ? 'message-user' : 'message-assistant'}
    >
      <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
        {message.content}
      </p>
    </motion.div>
  )
}
