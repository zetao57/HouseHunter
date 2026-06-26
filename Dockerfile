FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_AMAP_KEY=""
ENV VITE_AMAP_KEY=${VITE_AMAP_KEY}

RUN npm run build

FROM python:3.13-alpine AS production

WORKDIR /app

ENV DATABASE_PATH=/data/househunter.sqlite3
ENV PORT=80

COPY server.py ./server.py
COPY --from=build /app/dist ./dist

VOLUME ["/data"]
EXPOSE 80

CMD ["python", "server.py"]
