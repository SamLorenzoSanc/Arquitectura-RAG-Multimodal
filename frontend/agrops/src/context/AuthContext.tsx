import {
    createContext,
    useContext,
    useEffect,
    useState,
    ReactNode,
} from "react";

import { jwtDecode } from "jwt-decode";

import { login as loginService } from "@/services/auth.service";
import api from "@/api";

interface JwtPayload {
    sub: string;
    email: string;
    exp: number;
}

export interface User {
    id: string;
    name: string;
    email: string;
    exp: number;
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;

    login: (email: string, password: string) => Promise<void>;

    logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

async function loadCurrentUser(token: string): Promise<User> {
    const decoded = jwtDecode<JwtPayload>(token);

    const { data } = await api.get("/auth/me", {
        headers: {
            Authorization: `Bearer ${token}`,
        },
    });

    return {
        id: decoded.sub,
        exp: decoded.exp,
        email: data.email,
        name: data.name,
    };
}

export function AuthProvider({
    children,
}: {
    children: ReactNode;
}) {
    const [token, setToken] = useState<string | null>(() => localStorage.getItem("token"));

    const [user, setUser] = useState<User | null>(null);

    useEffect(() => {
        async function initialize() {
            const savedToken = localStorage.getItem("token");

            if (!savedToken) {
                setToken(null);
                setUser(null);
                return;
            }

            try {
                const decoded = jwtDecode<JwtPayload>(savedToken);

                if (decoded.exp * 1000 < Date.now()) {
                    localStorage.removeItem("token");
                    setToken(null);
                    setUser(null);
                    return;
                }

                const currentUser = await loadCurrentUser(savedToken);

                setToken(savedToken);
                setUser(currentUser);
            } catch {
                localStorage.removeItem("token");
                setToken(null);
                setUser(null);
            }
        }

        initialize();
    }, []);

    async function login(email: string, password: string) {
        const response = await loginService({
            email,
            password,
        });

        const jwt = response.access_token;

        localStorage.setItem("token", jwt);

        const currentUser = await loadCurrentUser(jwt);

        setToken(jwt);
        setUser(currentUser);
    }

    function logout() {
        localStorage.removeItem("token");
        sessionStorage.removeItem("token");

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
                isAuthenticated: !!token,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);

    if (!context)
        throw new Error("useAuth debe utilizarse dentro de AuthProvider");

    return context;
}