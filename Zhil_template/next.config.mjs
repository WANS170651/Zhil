/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  // 使用静态导出解决 Windows 权限问题
  output: 'export',
  distDir: '.next',
  trailingSlash: true,
  // 配置 API 路由代理到后端
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ]
  },
  // 配置静态资源
  assetPrefix: process.env.NODE_ENV === 'production' ? '' : '',
}

export default nextConfig
