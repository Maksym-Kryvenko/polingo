FROM node:20-alpine

WORKDIR /app

COPY frontend-app/package*.json ./
RUN npm install

COPY frontend-app .

# Don't set VITE_API_BASE_URL - let frontend determine it dynamically from window.location.hostname
ENV BROWSER=none

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173", "--strictPort"]
