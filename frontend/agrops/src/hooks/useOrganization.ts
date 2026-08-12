import { useQuery } from "@tanstack/react-query";
import { getOrganizations } from "@/services/organization.service";
import { queryKeys } from "@/lib/queryKeys";

export function useOrganizations() {
  return useQuery({
    queryKey: queryKeys.organizations,
    queryFn: getOrganizations,
  });
}
