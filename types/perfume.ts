
export interface PriceResult {
  site: string
  price: number | null
  size: string | null
  price_per_ml: number | null
  url: string
  stock_status: string
  image_url: string | null
}

export interface ComparisonResult {
  perfume_name: string
  results: PriceResult[]
  best_deal: PriceResult | null
}

export interface PerfumeSearch {
  name: string
}
