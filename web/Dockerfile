FROM node:22-slim AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# The /api rewrite target is fixed at build time.
ARG API_BASE_URL=http://api:8000
ENV API_BASE_URL=$API_BASE_URL
RUN npm run build

FROM node:22-slim
WORKDIR /web
ENV NODE_ENV=production
COPY --from=build /web ./
EXPOSE 3000
CMD ["npx", "next", "start", "-p", "3000", "-H", "0.0.0.0"]
