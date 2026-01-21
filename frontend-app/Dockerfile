FROM node:20-alpine

WORKDIR /app

COPY frontend-app/package*.json ./
RUN npm install

COPY frontend-app .

ENV VITE_API_BASE_URL="http://localhost:8000/api"
ENV BROWSER=none

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173", "--strictPort"]
