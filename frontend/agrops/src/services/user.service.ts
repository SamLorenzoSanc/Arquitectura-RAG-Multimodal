import api from "@/api";

export async function me() {

    const response = await api.get("/users/me");

    return response.data;
}

export async function listUsers() {

    const response = await api.get("/users/users");

    return response.data;
}