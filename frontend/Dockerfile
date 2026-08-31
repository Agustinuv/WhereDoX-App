FROM node:22-alpine

WORKDIR /srv

# Install from the lockfile first so the dependency layer survives source-only changes.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Next evaluates rewrites() at build time and writes the result into routes-manifest.json,
# so the backend address has to be known here — setting it only at runtime does nothing.
ARG BACKEND_URL=http://api:8000
ENV BACKEND_URL=$BACKEND_URL
RUN npm run build

EXPOSE 3000
CMD ["npm", "run", "start"]
