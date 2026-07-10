FROM node:20-slim AS build

WORKDIR /app

# CRACO was used by V1; install with --legacy-peer-deps to absorb the React 19
# + shadcn ecosystem that ships JSX-only ESLint configs in some optional deps.
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --legacy-peer-deps --no-audit --no-fund

ARG REACT_APP_BACKEND_URL=http://localhost:8000
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

COPY frontend/ ./
RUN npm run build 2>/dev/null || npx craco build 2>/dev/null || \
    npx vite build 2>/dev/null || \
    (echo "Could not detect build tool — ensure frontend exposes 'build' in package.json" && exit 1)


# ── Runtime stage: serve the static SPA ──────────────────────────────────
FROM node:20-slim AS runtime

WORKDIR /app

RUN npm install --no-audit --no-fund --global serve@14

COPY --from=build /app/build /app/build

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost:3000/ >/dev/null || exit 1

CMD ["serve", "-s", "build", "-l", "3000"]
