# The Next.js server, built as a small standalone server (next.config.ts `output`).
# API_BASE_URL is read when the server runs, so one image fits every server.
FROM node:24.22.1-alpine3.24 AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1 NEXT_OUTPUT=standalone
RUN npm run build

FROM node:24.22.1-alpine3.24
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
