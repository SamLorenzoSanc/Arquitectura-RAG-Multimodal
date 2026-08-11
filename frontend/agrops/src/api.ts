import axios from "axios";

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1",
});

api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem("token");

        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }

        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            const currentPath = window.location.pathname;
            if (!currentPath.includes("/login")) {
                console.warn("Token inválido o expirado. Redirigiendo a login...");
                localStorage.removeItem("token");
                sessionStorage.removeItem("token");
                window.location.href = "/login";
            }
        }
        if (error.response) {
            console.error(`API Error ${error.response.status}:`, error.response.data);
        }
        return Promise.reject(error);
    }
);

export default api;
