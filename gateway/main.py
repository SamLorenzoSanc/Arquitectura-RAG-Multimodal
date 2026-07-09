import uvicorn
# Esta función es una aplicación ASGI básica.
# Los servidores ASGI (como Uvicorn) esperan exactamente estos tres parámetros:
# - scope: Un diccionario con los datos de la petición (método HTTP, ruta, cabeceras, etc.)
# - receive: Una función asíncrona para recibir datos del cliente (ej. el cuerpo de un POST).
# - send: Una función asíncrona para enviar datos de vuelta al cliente.
async def app(scope, receive, send):
    body = "Hello, world!"
    # Convertimos el texto a bytes primero para asegurarnos de medir su tamaño real en bytes
    body_bytes = body.encode("utf-8")
    # Convertimos el número de la longitud a bytes (ej: 13 -> b"13")
    content_length = str(len(body_bytes)).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", b"text/plain"],
                [b"content-length",content_length],
            ],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": body_bytes,
        }
    )

def main():
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
