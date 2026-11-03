import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV === "development";

// Усе, що завантажує застосунок, — з нашого домену: шрифти self-hosted
// (next/font), фото й документи — через /media, діаграма — через BFF.
// Без nonce (вони зробили б кожну сторінку динамічною), тож inline-скрипти
// дозволені (зокрема скрипт теми next-themes). Головне, що це дає: заборона
// фреймів (clickjacking), плагінів, чужих <base> і цілей форм, запитів на
// сторонні адреси. Без upgrade-insecure-requests: прод і так лише HTTPS
// (nginx хоста + HSTS), а локальний прогін прод-стеку йде по HTTP.
const contentSecurityPolicy = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' blob: data:",
  "font-src 'self'",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const nextConfig: NextConfig = {
  // Самодостатній сервер для Docker-образу (frontend/Dockerfile)
  output: "standalone",
  // Без X-Powered-By: не підказуємо, на чому працює сервер
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "Content-Security-Policy", value: contentSecurityPolicy },
          // Для браузерів без frame-ancestors
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "same-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
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
