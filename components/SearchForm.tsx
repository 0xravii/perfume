
import { useState } from 'react'
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline'

interface SearchFormProps {
  onSearch: (perfumeName: string) => void
  loading: boolean
}

export default function SearchForm({ onSearch, loading }: SearchFormProps) {
  const [perfumeName, setPerfumeName] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (perfumeName.trim()) {
      onSearch(perfumeName.trim())
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative">
          <input
            type="text"
            value={perfumeName}
            onChange={(e) => setPerfumeName(e.target.value)}
            placeholder="Enter perfume name (e.g., Chanel No. 5, Dior Sauvage)"
            className="w-full pl-12 pr-32 py-4 text-lg border-2 border-gray-300 rounded-xl focus:border-primary-500 focus:ring-2 focus:ring-primary-200 focus:outline-none transition-all duration-200"
            disabled={loading}
          />
          <MagnifyingGlassIcon className="absolute left-4 top-1/2 transform -translate-y-1/2 h-6 w-6 text-gray-400" />
          <button
            type="submit"
            disabled={loading || !perfumeName.trim()}
            className="absolute right-2 top-1/2 transform -translate-y-1/2 btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <div className="flex items-center">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                Searching...
              </div>
            ) : (
              'Search'
            )}
          </button>
        </div>
      </form>
      
      <div className="mt-4 text-center">
        <p className="text-sm text-gray-500">
          We search across FragranceNet, FragranceX, FragranceShop and more
        </p>
      </div>
    </div>
  )
}
