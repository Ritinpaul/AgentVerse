/** @type {import('next').NextConfig} */
const cleanUrl = (url, fallback) => {
  const raw = url || fallback;
  return raw.replace(/^["']|["']$/g, '').replace(/\/+$/, '').trim();
};

const storeApi = cleanUrl(process.env.STORE_API_URL || process.env.NEXT_PUBLIC_STORE_API_URL, 'http://127.0.0.1:8005');
const controlApi = cleanUrl(process.env.CONTROL_API_URL || process.env.NEXT_PUBLIC_CONTROL_API_URL, 'http://127.0.0.1:8010');
const governanceApi = cleanUrl(process.env.GOVERNANCE_API_URL || process.env.NEXT_PUBLIC_GOVERNANCE_API_URL, 'http://127.0.0.1:8025');

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/store/:path*',
        destination: `${storeApi}/api/v1/:path*`,
      },
      {
        source: '/api/os/:path*',
        destination: `${controlApi}/api/v1/:path*`,
      },
      {
        source: '/api/govern/:path*',
        destination: `${governanceApi}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
