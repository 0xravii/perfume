
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:5000/:path*',
      },
    ]
  },
  images: {
    domains: ['www.fragrancenet.com', 'www.fragrancex.com', 'www.fragranceshop.com'],
  },
}

module.exports = nextConfig
