import { QueryClient } from "@tanstack/react-query";

/**
 * Caché de lecturas entre pestañas.
 * - staleTime Infinity: no refetch automático al remontar.
 * - refetchOnWindowFocus false: cambiar de pestaña del navegador no dispara fetch.
 * - Invalidación explícita solo tras create/update/delete.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: Infinity,
      gcTime: 1000 * 60 * 60,
      refetchOnWindowFocus: false,
      refetchOnReconnect: false,
      refetchOnMount: false,
      retry: 1,
    },
  },
});
