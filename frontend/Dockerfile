# Multi-stage: build the Vite app (API base baked to /api), then serve with Caddy.
FROM node:20-alpine AS build
WORKDIR /app

# API calls go to /api/* (same origin); Caddy strips the prefix and proxies to the API.
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package*.json ./
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build

FROM caddy:2-alpine
COPY --from=build /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile
EXPOSE 80 443
