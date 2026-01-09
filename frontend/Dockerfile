# Build Stage
FROM node:22-alpine as build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Production Stage
FROM nginx:alpine

# Copy built assets from build stage to a subfolder
RUN mkdir -p /usr/share/nginx/html/cryptotrader
COPY --from=build /app/dist /usr/share/nginx/html/cryptotrader

RUN echo 'server { \
    listen 80; \
    # Redirect root to /cryptotrader/ \
    location = / { \
    return 301 /cryptotrader/; \
    } \
    location /cryptotrader/ { \
    root /usr/share/nginx/html; \
    index index.html index.htm; \
    try_files $uri $uri/ /cryptotrader/index.html; \
    } \
    }' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
