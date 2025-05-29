from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Perfume Price Comparator", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PerfumeSearch(BaseModel):
    name: str

class PriceResult(BaseModel):
    site: str
    price: Optional[float]
    size: Optional[str]
    price_per_ml: Optional[float]
    url: str
    stock_status: str
    image_url: Optional[str]

class ComparisonResult(BaseModel):
    perfume_name: str
    results: List[PriceResult]
    best_deal: Optional[PriceResult]

# Site configurations
SITES = {
    "FragranceNet": {
        "base_url": "https://www.fragrancenet.com",
        "search_url": "https://www.fragrancenet.com/search?q={}",
    },
    "FragranceX": {
        "base_url": "https://www.fragrancex.com", 
        "search_url": "https://www.fragrancex.com/search?q={}",
    },
    "FragranceShop": {
        "base_url": "https://www.fragranceshop.com",
        "search_url": "https://www.fragranceshop.com/search?q={}",
    }
}

class PerfumeScraper:
    def __init__(self):
        self.session = None

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def extract_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from text"""
        if not price_text:
            return None
        # Remove currency symbols and extract numbers
        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
        if price_match:
            try:
                return float(price_match.group())
            except ValueError:
                return None
        return None

    def extract_size(self, size_text: str) -> Optional[str]:
        """Extract size information from text"""
        if not size_text:
            return None
        # Look for ml, oz patterns
        size_match = re.search(r'(\d+(?:\.\d+)?)\s*(ml|oz)', size_text.lower())
        if size_match:
            return f"{size_match.group(1)}{size_match.group(2)}"
        return None

    def calculate_price_per_ml(self, price: float, size_str: str) -> Optional[float]:
        """Calculate price per ml"""
        if not price or not size_str:
            return None

        size_match = re.search(r'(\d+(?:\.\d+)?)\s*(ml|oz)', size_str.lower())
        if size_match:
            size_num = float(size_match.group(1))
            unit = size_match.group(2)

            # Convert oz to ml if needed (1 oz = 29.5735 ml)
            if unit == 'oz':
                size_num *= 29.5735

            return round(price / size_num, 2) if size_num > 0 else None
        return None

    async def scrape_site(self, site_name: str, site_config: dict, query: str) -> List[PriceResult]:
        """Scrape a single site for perfume prices"""
        results = []

        try:
            search_url = site_config["search_url"].format(query.replace(' ', '%20'))

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            async with self.session.get(search_url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {site_name}: {response.status}")
                    return results

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Generic scraping - look for common price patterns
                price_elements = soup.find_all(['span', 'div'], class_=re.compile(r'price|cost|amount', re.I))[:5]

                for i, price_elem in enumerate(price_elements):
                    price_text = price_elem.get_text(strip=True)
                    price = self.extract_price(price_text)

                    if price and price > 0:
                        # Try to find size info nearby
                        size_text = ""
                        parent = price_elem.parent
                        if parent:
                            size_text = parent.get_text()

                        size = self.extract_size(size_text)
                        price_per_ml = self.calculate_price_per_ml(price, size) if size else None

                        result = PriceResult(
                            site=site_name,
                            price=price,
                            size=size,
                            price_per_ml=price_per_ml,
                            url=search_url,
                            stock_status="Available",
                            image_url=None
                        )
                        results.append(result)

                        if len(results) >= 3:  # Limit results per site
                            break

        except Exception as e:
            logger.error(f"Error scraping {site_name}: {e}")

        return results

scraper = PerfumeScraper()

@app.get("/")
async def root():
    return {"message": "Perfume Price Comparator API"}

@app.post("/search", response_model=ComparisonResult)
async def search_perfume(search: PerfumeSearch):
    """Search for perfume prices across multiple sites"""

    if not search.name.strip():
        raise HTTPException(status_code=400, detail="Perfume name is required")

    query = search.name.strip()
    all_results = []

    async with PerfumeScraper() as scraper_instance:
        # Create tasks for concurrent scraping
        tasks = []
        for site_name, site_config in SITES.items():
            task = scraper_instance.scrape_site(site_name, site_config, query)
            tasks.append(task)

        # Execute all scraping tasks concurrently
        site_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        for site_name, results in zip(SITES.keys(), site_results):
            if isinstance(results, Exception):
                logger.error(f"Error scraping {site_name}: {results}")
                continue
            all_results.extend(results)

    # Find best deal (lowest price per ml, or lowest price if no size info)
    best_deal = None
    if all_results:
        # Prefer results with price_per_ml data
        results_with_ppm = [r for r in all_results if r.price_per_ml is not None]
        if results_with_ppm:
            best_deal = min(results_with_ppm, key=lambda x: x.price_per_ml)
        else:
            # Fall back to lowest price
            best_deal = min(all_results, key=lambda x: x.price)

    return ComparisonResult(
        perfume_name=query,
        results=all_results,
        best_deal=best_deal
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)