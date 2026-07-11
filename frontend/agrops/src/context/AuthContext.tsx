import {createContext, useContext, useEffect, useState, ReactNode} from "react";

import { jwtDecode } from "jwt-decode";
import { login as loginService } from "@/services/auth.service";

interface User {
    id: string;
    email: string;
    exp: number;
}

interface AuthContextType {
    user: User | null;
    token: string |null;
    isAuthenticated: boolean;

    login: (email: string, password: string) => Promise<void>;

    logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({
    children,
}: {
    children: ReactNode;
}) {

    const [token, setToken] = useState<string | null>(null);

    const [user, setUser] = useState<User | null>(null);

    useEffect(() => {

        const savedToken = localStorage.getItem("token");

        if (!savedToken)
            return;

        try {

            const decoded = jwtDecode<User>(savedToken);

            if (decoded.exp * 1000 < Date.now()) {

                localStorage.removeItem("token");

                return;

            }

            setToken(savedToken);

            setUser(decoded);

        } catch {

            localStorage.removeItem("token");

        }

    }, []);

    async function login(
        email: string,
        password: string,
    ) {
        const response = await loginService({
            email,
            password,
        });
        const jwt = response.access_token;
        const decoded = jwtDecode<User>(jwt);
        localStorage.setItem("token", jwt);
        setToken(jwt);
        setUser(decoded);

    }

    function logout() {
        localStorage.removeItem("token");
        setToken(null);
        setUser(null);
    }

    return (

        <AuthContext.Provider
            value={{
                user,
                token,
                login,
                logout,
                isAuthenticated: !!user,
            }}
        >
            {children}
        </AuthContext.Provider>

    );

}

export function useAuth() {

    const context = useContext(AuthContext);

    if (!context)
        throw new Error(
            "useAuth debe utilizarse dentro de AuthProvider"
        );

    return context;

}