FROM node:20-slim

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .

CMD ["npx", "next", "dev", "--hostname", "0.0.0.0"]
