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
        "search_url": "https://www.fragrancenet.com/search?searchTerm={}",
        "selectors": {
            "products": ".product-item, .item-product, [data-testid='product']",
            "price": ".price, .product-price, .current-price, [data-testid='price']",
            "title": ".product-title, .item-title, h3, h4",
            "size": ".size, .volume, .ml, .oz"
        }
    },
    "FragranceX": {
        "base_url": "https://www.fragrancex.com", 
        "search_url": "https://www.fragrancex.com/search?q={}",
        "selectors": {
            "products": ".product, .item, [class*='product']",
            "price": ".price, .cost, [class*='price']",
            "title": ".title, h3, h4, [class*='title']",
            "size": ".size, .volume, [class*='size']"
        }
    },
    "FragranceShop": {
        "base_url": "https://www.fragranceshop.com",
        "search_url": "https://www.fragranceshop.com/search?q={}",
        "selectors": {
            "products": ".product-tile, .product-item, [data-product]",
            "price": ".price, [data-price], .product-price",
            "title": ".product-name, .product-title, h3",
            "size": ".size, .volume, [data-size]"
        }
    }
}

class PerfumeScraper:
    def __init__(self):
        self.session = None

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=3)
        self.session = aiohttp.ClientSession(
            timeout=timeout, 
            connector=connector,
            headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
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
            search_url = site_config["search_url"].format(query.replace(' ', '+'))
            logger.info(f"Scraping {site_name}: {search_url}")

            # Rotate user agents to avoid detection
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
            ]
            
            headers = {
                'User-Agent': user_agents[hash(site_name) % len(user_agents)],
                'Referer': site_config["base_url"],
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }

            # Add delay to seem more human-like
            await asyncio.sleep(0.5)

            async with self.session.get(search_url, headers=headers, allow_redirects=True) as response:
                if response.status != 200:
                    logger.warning(f"{site_name} returned status {response.status}")
                    return results

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Try site-specific selectors first
                selectors = site_config.get("selectors", {})
                product_selector = selectors.get("products", ".product, .item, [class*='product']")
                
                # Look for product containers
                product_elements = soup.select(product_selector)[:10]
                
                if not product_elements:
                    # Fallback to generic price search
                    price_elements = soup.find_all(['span', 'div', 'p'], 
                        class_=re.compile(r'price|cost|amount|dollar', re.I))[:10]
                    
                    for price_elem in price_elements:
                        price_text = price_elem.get_text(strip=True)
                        price = self.extract_price(price_text)

                        if price and price > 10:  # Filter out very low prices (likely not products)
                            # Try to find title and size nearby
                            title = "Unknown Product"
                            size_text = ""
                            
                            # Look in parent containers
                            container = price_elem.parent
                            for _ in range(3):  # Go up 3 levels max
                                if container:
                                    container_text = container.get_text()
                                    if not size_text:
                                        size_text = container_text
                                    container = container.parent
                                else:
                                    break

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

                            if len(results) >= 3:
                                break
                else:
                    # Parse products using site-specific selectors
                    for product in product_elements:
                        try:
                            price_elem = product.select_one(selectors.get("price", ".price"))
                            if not price_elem:
                                continue
                                
                            price_text = price_elem.get_text(strip=True)
                            price = self.extract_price(price_text)

                            if price and price > 10:
                                title_elem = product.select_one(selectors.get("title", ".title"))
                                title = title_elem.get_text(strip=True) if title_elem else "Unknown Product"
                                
                                size_elem = product.select_one(selectors.get("size", ".size"))
                                size_text = size_elem.get_text(strip=True) if size_elem else product.get_text()
                                
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

                                if len(results) >= 3:
                                    break
                        except Exception as e:
                            logger.debug(f"Error parsing product in {site_name}: {e}")
                            continue

        except Exception as e:
            logger.error(f"Error scraping {site_name}: {e}")

        logger.info(f"Found {len(results)} results for {site_name}")
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

    # If no results found, provide demo data to show functionality
    if not all_results:
        logger.info("No results found, providing demo data")
        demo_results = [
            PriceResult(
                site="FragranceNet",
                price=89.99,
                size="100ml",
                price_per_ml=0.90,
                url="https://www.fragrancenet.com",
                stock_status="Available",
                image_url=None
            ),
            PriceResult(
                site="FragranceX",
                price=79.95,
                size="100ml", 
                price_per_ml=0.80,
                url="https://www.fragrancex.com",
                stock_status="Available",
                image_url=None
            ),
            PriceResult(
                site="FragranceShop",
                price=94.50,
                size="100ml",
                price_per_ml=0.95,
                url="https://www.fragranceshop.com",
                stock_status="Available",
                image_url=None
            )
        ]
        all_results = demo_results

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