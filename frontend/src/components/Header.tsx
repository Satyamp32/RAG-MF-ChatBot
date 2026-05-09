import React from 'react'
import { motion } from 'framer-motion'
import { Menu, Activity } from 'lucide-react'
import { toast } from 'react-hot-toast'

interface HeaderProps {
  onMenuToggle: () => void
  isHealthy: boolean
}

export default function Header({ onMenuToggle, isHealthy }: HeaderProps) {
  return (
    <motion.header
      initial={{ y: -20 }}
      animate={{ y: 0 }}
      className="bg-background-secondary border-b border-border sticky top-0 z-40"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo and Title */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-accent rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">MF</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-text">
                Mutual Fund Assistant
              </h1>
              <p className="text-sm text-text-secondary">
                AI-powered factual answers
              </p>
            </div>
          </div>

          {/* Right Side */}
          <div className="flex items-center gap-4">
            {/* Health Status */}
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-success' : 'bg-error'}`} />
              <span className="text-xs text-text-secondary">
                {isHealthy ? 'Connected' : 'Offline'}
              </span>
            </div>

            {/* Menu Button */}
            <button
              onClick={onMenuToggle}
              className="p-2 hover:bg-background-hover rounded-lg transition-colors lg:hidden"
            >
              <Menu className="w-5 h-5 text-text" />
            </button>
          </div>
        </div>
      </div>
    </motion.header>
  )
}
