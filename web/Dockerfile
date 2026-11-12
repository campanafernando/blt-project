FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund

COPY . .
RUN npm run build

FROM nginx:1.27-alpine
# nginx renders templates/*.template with these variables at start; Railway overrides PORT and
# API_UPSTREAM. The last one makes the image export NGINX_LOCAL_RESOLVERS from /etc/resolv.conf.
ENV PORT=80 API_UPSTREAM=http://api:8000 NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=15s --timeout=3s --retries=5 CMD wget -qO- http://127.0.0.1:${PORT}/ >/dev/null || exit 1
