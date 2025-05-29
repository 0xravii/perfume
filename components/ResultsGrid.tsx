
import { ComparisonResult, PriceResult } from '../types/perfume'
import PriceCard from './PriceCard'

interface ResultsGridProps {
  results: ComparisonResult
}

export default function ResultsGrid({ results }: ResultsGridProps) {
  const { perfume_name, results: priceResults, best_deal } = results

  if (!priceResults || priceResults.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-6xl mb-4">😔</div>
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">No results found</h2>
        <p className="text-gray-600">
          Try searching with a different perfume name or check the spelling
        </p>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-gray-900 mb-2">
          Results for "{perfume_name}"
        </h2>
        <p className="text-gray-600">
          Found {priceResults.length} result{priceResults.length !== 1 ? 's' : ''} across multiple retailers
        </p>
      </div>

      {/* Best Deal Banner */}
      {best_deal && (
        <div className="mb-8 p-6 bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-200 rounded-xl">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center mb-2">
                <span className="text-2xl mr-2">🏆</span>
                <h3 className="text-xl font-semibold text-green-800">Best Deal Found!</h3>
              </div>
              <p className="text-green-700">
                <span className="font-medium">{best_deal.site}</span> - 
                ${best_deal.price?.toFixed(2)}
                {best_deal.price_per_ml && (
                  <span className="ml-2 text-sm">
                    (${best_deal.price_per_ml}/ml)
                  </span>
                )}
              </p>
            </div>
            <a
              href={best_deal.url}
              target="_blank"
              rel="noopener noreferrer"
              className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg font-medium transition-colors duration-200"
            >
              View Deal
            </a>
          </div>
        </div>
      )}

      {/* Results Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {priceResults.map((result, index) => (
          <PriceCard 
            key={`${result.site}-${index}`} 
            result={result} 
            isBestDeal={best_deal?.site === result.site && best_deal?.price === result.price}
          />
        ))}
      </div>

      {/* Footer Info */}
      <div className="mt-12 text-center">
        <p className="text-sm text-gray-500">
          Prices are updated in real-time. Click "View Deal" to visit the retailer's website.
        </p>
      </div>
    </div>
  )
}
