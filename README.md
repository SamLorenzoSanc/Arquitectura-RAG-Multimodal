# API 

# Construir la imagen en docker
docker build -t [api-gateway] .

# Levantar el contenedor de la api por el puerto 8000
docker run -p 8000:8000 api-gateway

# Comando para identificar el puerto abierto y borrarlo de memoria
netstat -ano | findstr 8000
taskkill /F /PID 2716

# Levantar el servidor web de desarrollo en local
(powershell) python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Construir la imagen en docker
docker build -t [postgres_db] .

# Levantar el contenedor de la base de datos postgres 
docker run -p 5432:5432 -e POSTGRES_DB=agrops -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres postgres_db

# Levantar el contenedor de la interfaz básica con python
docker build -t agrotech-app .
