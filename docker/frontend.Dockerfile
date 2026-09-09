FROM node:22-slim
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend .
ENV API_BASE_URL=http://backend:8000
RUN npm run build
CMD ["npm", "run", "start"]
