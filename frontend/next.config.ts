import type { NextConfig } from 'next';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const nextConfig: NextConfig = {
  // Pin discovery to this app so unrelated lockfiles above the repository cannot affect builds.
  turbopack: {
    root: dirname(fileURLToPath(import.meta.url)),
  },
};

export default nextConfig;
