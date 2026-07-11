# API 

# Construir la imagen en docker
docker build -t [name] .

# Levantar el contenedor por el puerto 8000
docker run -p 8000:8000 api-gateway

# Comando para identificar el puerto abierto y borrarlo de memoria
netstat -ano | findstr 8000
taskkill /F /PID 2716