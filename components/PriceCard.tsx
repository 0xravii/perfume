
import { PriceResult } from '../types/perfume'

interface PriceCardProps {
  result: PriceResult
  isBestDeal?: boolean
}

export default function PriceCard({ result, isBestDeal }: PriceCardProps) {
  const { site, price, size, price_per_ml, url, stock_status, image_url } = result

  return (
    <div className={`price-card relative ${isBestDeal ? 'ring-2 ring-green-400 bg-green-50' : ''}`}>
      {isBestDeal && (
        <div className="absolute -top-2 -right-2 bg-green-500 text-white px-2 py-1 rounded-full text-xs font-medium">
          Best Deal
        </div>
      )}
      
      {/* Site Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-lg text-gray-900">{site}</h3>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
          stock_status === 'In Stock' 
            ? 'bg-green-100 text-green-800' 
            : 'bg-red-100 text-red-800'
        }`}>
          {stock_status}
        </span>
      </div>

      {/* Image placeholder */}
      <div className="w-full h-32 bg-gray-100 rounded-lg mb-4 flex items-center justify-center">
        {image_url ? (
          <img 
            src={image_url} 
            alt="Perfume" 
            className="max-h-full max-w-full object-contain rounded-lg"
            onError={(e) => {
              e.currentTarget.style.display = 'none'
              e.currentTarget.nextElementSibling?.classList.remove('hidden')
            }}
          />
        ) : null}
        <div className={`text-gray-400 text-sm ${image_url ? 'hidden' : ''}`}>
          🌸 No image
        </div>
      </div>

      {/* Price Information */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-2xl font-bold text-gray-900">
            ${price?.toFixed(2)}
          </span>
          {size && (
            <span className="text-sm text-gray-600 bg-gray-100 px-2 py-1 rounded">
              {size}
            </span>
          )}
        </div>

        {price_per_ml && (
          <div className="text-sm text-gray-600">
            <span className="font-medium">${price_per_ml}/ml</span>
          </div>
        )}

        {/* Action Button */}
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="w-full bg-primary-600 hover:bg-primary-700 text-white py-2 px-4 rounded-lg font-medium transition-colors duration-200 flex items-center justify-center"
        >
          <span>View on {site}</span>
          <span className="ml-2">↗</span>
        </a>
      </div>
    </div>
  )
}
