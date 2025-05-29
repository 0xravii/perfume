
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
        "search_url": "https://www.fragrancenet.com/search?searchTerm={query}",
        "selectors": {
            "products": ".product-item",
            "name": ".product-name",
            "price": ".price",
            "image": ".product-image img"
        }
    },
    "FragranceX": {
        "base_url": "https://www.fragrancex.com",
        "search_url": "https://www.fragrancex.com/search?q={query}",
        "selectors": {
            "products": ".product",
            "name": ".product-title",
            "price": ".price-current",
            "image": ".product-image img"
        }
    },
    "FragranceShop": {
        "base_url": "https://www.fragranceshop.com",
        "search_url": "https://www.fragranceshop.com/search?q={query}",
        "selectors": {
            "products": ".product-item",
            "name": ".product-name",
            "price": ".price",
            "image": ".product-image img"
        }
    }
}

class PerfumeScraper:
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=10)
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def extract_price(self, price_text: str) -> Optional[float]:
        """Extract price from text"""
        if not price_text:
            return None
        
        # Remove currency symbols and extract number
        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
        if price_match:
            try:
                return float(price_match.group())
            except ValueError:
                return None
        return None
    
    def extract_size(self, text: str) -> Optional[str]:
        """Extract size from product text"""
        size_patterns = [
            r'(\d+(?:\.\d+)?)\s*ml',
            r'(\d+(?:\.\d+)?)\s*oz',
            r'(\d+(?:\.\d+)?)\s*fl\s*oz'
        ]
        
        for pattern in size_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group()
        return None
    
    def calculate_price_per_ml(self, price: float, size_text: str) -> Optional[float]:
        """Calculate price per ml"""
        if not size_text:
            return None
        
        # Extract numeric value and unit
        size_match = re.search(r'(\d+(?:\.\d+)?)\s*(ml|oz|fl\s*oz)', size_text, re.IGNORECASE)
        if not size_match:
            return None
        
        size_value = float(size_match.group(1))
        unit = size_match.group(2).lower().replace(' ', '')
        
        # Convert to ml if needed
        if 'oz' in unit:
            size_value *= 29.5735  # Convert oz to ml
        
        if size_value > 0:
            return round(price / size_value, 2)
        return None
    
    async def scrape_site(self, site_name: str, site_config: Dict, query: str) -> List[PriceResult]:
        """Scrape a single site for perfume prices"""
        results = []
        
        try:
            search_url = site_config["search_url"].format(query=query.replace(' ', '+'))
            logger.info(f"Scraping {site_name}: {search_url}")
            
            async with self.session.get(search_url) as response:
                if response.status != 200:
                    logger.warning(f"{site_name} returned status {response.status}")
                    return results
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                products = soup.select(site_config["selectors"]["products"])[:5]  # Limit to 5 results per site
                
                for product in products:
                    try:
                        name_elem = product.select_one(site_config["selectors"]["name"])
                        price_elem = product.select_one(site_config["selectors"]["price"])
                        image_elem = product.select_one(site_config["selectors"]["image"])
                        
                        if not name_elem or not price_elem:
                            continue
                        
                        name = name_elem.get_text(strip=True)
                        price_text = price_elem.get_text(strip=True)
                        price = self.extract_price(price_text)
                        
                        if not price:
                            continue
                        
                        # Extract size from name or other elements
                        size = self.extract_size(name)
                        price_per_ml = self.calculate_price_per_ml(price, size) if size else None
                        
                        # Get product URL
                        link_elem = product.find('a')
                        product_url = ""
                        if link_elem and link_elem.get('href'):
                            href = link_elem['href']
                            if href.startswith('/'):
                                product_url = site_config["base_url"] + href
                            else:
                                product_url = href
                        
                        # Get image URL
                        image_url = ""
                        if image_elem and image_elem.get('src'):
                            src = image_elem['src']
                            if src.startswith('/'):
                                image_url = site_config["base_url"] + src
                            else:
                                image_url = src
                        
                        result = PriceResult(
                            site=site_name,
                            price=price,
                            size=size,
                            price_per_ml=price_per_ml,
                            url=product_url,
                            stock_status="In Stock",  # Simplified for now
                            image_url=image_url
                        )
                        results.append(result)
                        
                    except Exception as e:
                        logger.error(f"Error processing product from {site_name}: {e}")
                        continue
                        
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
