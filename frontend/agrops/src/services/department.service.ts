import api from "@/api";

export const getDepartments = async (
    organizationId: string,
) => {

    const { data } = await api.get(
        `/department/organization/${organizationId}`
    );

    return data;
};

export const getDepartmentMembers = async (
    departmentId: string,
) => {

    const { data } = await api.get(
        `/department/${departmentId}/members`
    );

    return data;
};