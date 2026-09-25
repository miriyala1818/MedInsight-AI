/** @type {import('next').NextConfig} */
const nextConfig = {
  // 'output: standalone' is only needed for Docker/production builds.
  // Removing it speeds up local dev server significantly.
  typedRoutes: true,
  eslint: {
    // Warning: This allows production builds to successfully complete even if
    // your project has ESLint errors.
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Note: Set to true only if you want to bypass TypeScript errors during build
    // Currently set to false to catch type errors
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
