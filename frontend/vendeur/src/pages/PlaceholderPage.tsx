import { useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Construction } from 'lucide-react'

export default function PlaceholderPage() {
  const location = useLocation()
  const pageName = location.pathname.split('/').pop() || ''
  const title = pageName.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())

  return (
    <div className="p-8">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex flex-col items-center justify-center h-96"
      >
        <Construction className="w-16 h-16 text-gray-300 mb-4" />
        <h1 className="text-xl font-semibold text-gray-700">{title}</h1>
        <p className="text-gray-400 mt-2">Cette page est en cours de construction</p>
      </motion.div>
    </div>
  )
}
