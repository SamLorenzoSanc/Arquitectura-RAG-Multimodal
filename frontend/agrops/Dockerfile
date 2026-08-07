# --- ETAPA 1: Construcción ---
FROM node:20-alpine AS build

WORKDIR /app

RUN npm install -g pnpm

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm run build


# --- ETAPA 2: Servidor ---
FROM node:20-alpine

WORKDIR /app

# Instalamos el servidor estático globalmente
RUN npm install -g serve

# Copiamos SOLO la carpeta compilada desde la etapa anterior
# (Cambia "dist" por "build" si tu framework genera esa carpeta)
COPY --from=build /app/dist ./dist

EXPOSE 80

# Ejecutamos el servidor en el puerto 80 apuntando a la carpeta compilada
CMD ["serve", "-s", "dist", "-l", "80"]