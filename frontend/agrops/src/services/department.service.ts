import api from "@/api";

export interface Department {
    id: string;
    organization_id: string;
    name: string;
    description?: string;
    members?: number;
}

export interface DepartmentMember {
    id: string;
    name: string;
    email: string;
}

class DepartmentService {
    async list(
        organizationId: string
    ): Promise<Department[]> {

        const { data } = await api.get(
            `/department/organization/${organizationId}`
        );

        return data;
    }

    async get(
        departmentId: string
    ): Promise<Department> {

        const { data } = await api.get(
            `/department/${departmentId}`
        );

        return data;
    }

    async create(
        payload: {
            organization_id: string;
            name: string;
            description?: string;
        }
    ): Promise<Department> {

        const { data } = await api.post(
            "/department",
            payload
        );

        return data;
    }

    async update(
        departmentId: string,
        payload: {
            name: string;
            description?: string;
        }
    ) {

        const { data } = await api.put(
            `/department/${departmentId}`,
            payload
        );

        return data;
    }

    async delete(
        departmentId: string
    ) {

        await api.delete(
            `/department/${departmentId}`
        );

    }

    async members(
        departmentId: string
    ): Promise<DepartmentMember[]> {

        const { data } = await api.get(
            `/department/${departmentId}/members`
        );

        return data.items;
    }

    async addMember(
        departmentId: string,
        payload: {
            user_id: string;
        }
    ) {

        const { data } = await api.post(
            `/department/${departmentId}/members`,
            payload
        );

        return data;
    }

    async removeMember(
        departmentId: string,
        userId: string
    ) {

        await api.delete(
            `/department/${departmentId}/members/${userId}`
        );

    }

    async availableUsers(
        departmentId: string
    ) {

        const { data } = await api.get(
            `/department/${departmentId}/available-users`
        );

        return data.items;
    }

    async userDepartments(
        userId: string
    ): Promise<Department[]> {

        const { data } = await api.get(
            `/department/user/${userId}`
        );

        return data.items;
    }
}

export default new DepartmentService();