
import { useState } from 'react'
import Head from 'next/head'
import SearchForm from '../components/SearchForm'
import ResultsGrid from '../components/ResultsGrid'
import { ComparisonResult } from '../types/perfume'

export default function Home() {
  const [results, setResults] = useState<ComparisonResult | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSearch = async (perfumeName: string) => {
    setLoading(true)
    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: perfumeName }),
      })
      
      if (!response.ok) {
        throw new Error('Search failed')
      }
      
      const data = await response.json()
      setResults(data)
    } catch (error) {
      console.error('Search error:', error)
      alert('Search failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Head>
        <title>Perfume Price Comparator</title>
        <meta name="description" content="Find the best deals on perfumes across multiple retailers" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="container mx-auto px-4 py-8">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-4">
              🌸 Perfume Price Finder
            </h1>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Find the best deals on your favorite fragrances across multiple retailers
            </p>
          </div>

          {/* Search Form */}
          <SearchForm onSearch={handleSearch} loading={loading} />

          {/* Results */}
          {results && (
            <div className="mt-12">
              <ResultsGrid results={results} />
            </div>
          )}
        </div>
      </main>
    </>
  )
}
