import { useQuery } from "@tanstack/react-query";

import { getDepartmentMembers } from "@/services/department.service";

export function useDepartmentMembers(
    departmentId?: string,
) {
    return useQuery({
        queryKey: [
            "department-members",
            departmentId,
        ],

        enabled: !!departmentId,

        queryFn: () =>
            getDepartmentMembers(
                departmentId!,
            ),
    });
}