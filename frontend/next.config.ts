import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Самодостатній сервер для Docker-образу (frontend/Dockerfile)
  output: "standalone",
  // Без X-Powered-By: не підказуємо, на чому працює сервер
  poweredByHeader: false,
  cacheComponents: true,
  partialPrefetching: true,
  // URL бекенду (Django) закінчуються на "/", тож BFF-проксі /api/backend/*
  // має отримувати шлях як є. Слеш для сторінок нормалізує src/proxy.ts.
  skipTrailingSlashRedirect: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
