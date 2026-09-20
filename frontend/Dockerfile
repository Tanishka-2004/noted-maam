# ==============================================================================
# Stage 1: dependency installer & builder
# ==============================================================================
FROM node:20-alpine AS builder

WORKDIR /build

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
# Disable telemetry during build
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build


# ==============================================================================
# Stage 2: runner image
# ==============================================================================
FROM node:20-alpine AS final

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    NEXT_TELEMETRY_DISABLED=1

# Copy build output and package configurations from builder
COPY --from=builder /build/package.json ./
COPY --from=builder /build/.next/standalone ./
COPY --from=builder /build/.next/static ./.next/static
COPY --from=builder /build/public ./public

# Set non-root context
USER node

EXPOSE 3000

# Node-native Healthcheck client (no curl/wget dependency)
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000', (res) => { if (res.statusCode === 200 || res.statusCode === 307) process.exit(0); else process.exit(1); }).on('error', () => process.exit(1))"

CMD ["node", "server.js"]
