# ---- Phase 2F Step 11: InsightForge Next.js frontend production image ----
#
# Builds the existing Next.js app in production mode and serves the standalone
# build (`output: "standalone"`). The browser talks to the backend through the
# published host port, so the API base URL is baked at build time via an
# ARG (default http://localhost:8000, overridable per environment).
#
# 1. deps    — install exact dependencies (npm ci).
# 2. builder — run the production build (next build).
# 3. runner  — minimal runtime: standalone server + static assets + public/.
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
