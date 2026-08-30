FROM node:20-alpine AS build

WORKDIR /app

# Misma origen que Nginx: el navegador llama a /api/v1 en el puerto 80.
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=$VITE_API_URL

# Pin a pnpm 10: `npm i -g pnpm` instala 11+, que falla con ERR_PNPM_IGNORED_BUILDS
# si Cypress (e2e local) no está en allowBuilds. Aquí no se usa su binario.
RUN npm install -g pnpm@10

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
ENV CYPRESS_INSTALL_BINARY=0
RUN pnpm install --frozen-lockfile --config.strict-dep-builds=false

COPY . .
RUN pnpm run build


FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --retries=5 --start-period=10s \
  CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
