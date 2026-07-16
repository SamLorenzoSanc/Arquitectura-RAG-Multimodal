import { useQuery } from "@tanstack/react-query";

import { getOrganizations } from "@/services/organization.service";

export function useOrganizations() {
    return useQuery({
        queryKey: ["organization"],
        queryFn: getOrganizations,
    });
}