import api from "@/api";

export interface LoginRequest {
    email: string;
    password: string;
}

export interface LoginResponse {
    access_token: string;
    expires_in: number;
}

export async function login(request: LoginRequest) {

    const response = await api.post<LoginResponse>(
        "/auth/login",
        request
    );

    return response.data;
}

export async function register(data: unknown) {

    const response = await api.post(
        "/auth/register",
        data
    );

    return response.data;
}