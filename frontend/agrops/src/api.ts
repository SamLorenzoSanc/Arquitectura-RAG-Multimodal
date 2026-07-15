import axios from "axios";

// 1. Crear la instancia base de Axios
const api = axios.create({
    baseURL: "http://localhost:8000/api/v1", // Tu URL del backend
});

// 2. Configurar el Interceptor para incluir el Token Bearer automáticamente
api.interceptors.request.use(
    (config) => {
        // Busca el token donde lo estés guardando al hacer login
        // Por ejemplo, en el localStorage bajo la llave "token"
        const token = localStorage.getItem("token"); 

        if (token) {
            // Inyecta el token en las cabeceras de la petición actual
            // El formato estándar suele ser: Bearer tu_jwt_token
            config.headers.Authorization = `Bearer ${token}`;
        }
        
        return config;
    },
    (error) => {
        // Manejar el error de la petición antes de que se envíe
        return Promise.reject(error);
    }
);

// 3. Configurar el Interceptor de respuesta para manejar errores de autenticación
api.interceptors.response.use(
    (response) => response,
    (error) => {
        // Si el error es 401 (no autorizado)
        if (error.response?.status === 401) {
            // Solo redirigir si no estamos ya en login y el error es realmente de autenticación
            const currentPath = window.location.pathname;
            if (!currentPath.includes("/login")) {
                console.warn("Token inválido o expirado. Redirigiendo a login...");
                localStorage.removeItem("token");
                sessionStorage.removeItem("token");
                window.location.href = "/login";
            }
        }
        // Log de errores para debugging
        if (error.response) {
            console.error(`API Error ${error.response.status}:`, error.response.data);
        }
        return Promise.reject(error);
    }
);

export default api;