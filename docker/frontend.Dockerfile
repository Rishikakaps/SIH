FROM node:22-slim
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend .
RUN npm run build
CMD ["npm", "run", "start"]
