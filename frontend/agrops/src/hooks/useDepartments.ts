import { useQuery } from "@tanstack/react-query";

import { getDepartments } from "@/services/department.service";

export function useDepartments(
    organizationId?: string,
) {
    return useQuery({
        queryKey: [
            "departments",
            organizationId,
        ],

        enabled: !!organizationId,

        queryFn: () =>
            getDepartments(
                organizationId!,
            ),
    });
}