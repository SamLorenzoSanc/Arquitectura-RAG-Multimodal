"use client";

import { useEffect, useState, type FormEvent } from "react";
import api from "@/api";
import { useOrganization } from "@/context/OrganizationContext";
import DepartmentService from "@/services/department.service";

interface Organization {
    id: string;
    name: string;
    description?: string;
    status: string;
}

interface Department {
    id: string;
    name: string;
    description?: string;
    members?: number;
}

interface Member {
    id: string;
    name: string;
    email: string;
    role?: string;
}

interface RoleOption {
    id: string;
    name: string;
    description?: string;
    organization_id?: string;
}

// --- DEFINICIÓN DE ROLES OPERATIVOS Y ACCESO RAG ---
const ROLE_DEFINITIONS: Record<string, { label: string; context: string }> = {
    "ORG_ADMIN": { 
        label: "Administrador de Organización", 
        context: "Acceso Total RAG" 
    },
    "FARM_MANAGER": { 
        label: "Gestor de Fincas / Producción", 
        context: "RAG: Fincas, Cultivos e IGP" 
    },
    "LOGISTICS_OPERATOR": { 
        label: "Operador Logístico", 
        context: "RAG: Flota, Rutas y Contenedores" 
    },
    "QUALITY_CONTROLLER": { 
        label: "Controlador de Calidad", 
        context: "RAG: Cadena de Frío e Inspección" 
    },
    "USER": { 
        label: "Usuario Estándar", 
        context: "Consulta básica" 
    }
};

// --- SERVICIOS DE API GATEWAY ---
export const getOrganizations = async () => {
    const { data } = await api.get("/organization");
    return data;
};

export const getOrganizationMembers = async (id: string) => {
    const { data } = await api.get(`/organization/${id}/members`);
    return data;
};

export const getDepartments = async (id: string) => {
    const { data } = await api.get(`/department/organization/${id}`);
    return data;
};

export const deleteOrganization = async (id: string) => {
    await api.delete(`/organization/${id}`);
};

export const getRoles = async () => {
    const { data } = await api.get("/users/roles");
    return data;
};

export const createDepartment = async (payload: { organization_id: string; name: string; description?: string }) => {
    const { data } = await api.post("/department", payload);
    return data;
};

export const addDepartmentMember = async (departmentId: string, payload: { email: string; role_id?: string }) => {
    const { data } = await api.post(`/department/${departmentId}/members`, payload);
    return data;
};

export default function OrganizationPage() {
    const {
        selectedOrg,
        setSelectedOrg,
        organizations,
        setOrganizations,
    } = useOrganization();

    const [activeDept, setActiveDept] = useState<Department | null>(null);
    const [roles, setRoles] = useState<RoleOption[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [orgDetails, setOrgDetails] = useState<Record<string, { departments: Department[]; roles: RoleOption[]; members: Member[]; departmentMembers: Record<string, Member[]>; activeDeptId: string | null }>>({});
    
    // Modales y formularios
    const [showDeptModal, setShowDeptModal] = useState(false);
    const [showMemberModal, setShowMemberModal] = useState(false);
    const [departmentName, setDepartmentName] = useState("");
    const [departmentDescription, setDepartmentDescription] = useState("");
    
    const [selectedUserEmail, setSelectedUserEmail] = useState("");
    const [selectedRoleId, setSelectedRoleId] = useState("");
    
    const [submittingDepartment, setSubmittingDepartment] = useState(false);
    const [submittingMember, setSubmittingMember] = useState(false);
    const [expandedOrgId, setExpandedOrgId] = useState<string | null>(null);

    // Carga inicial optimizada cargando organizaciones y roles globales en paralelo
    useEffect(() => {
        let isMounted = true;
        const fetchInitialData = async () => {
            try {
                setLoading(true);
                const [orgsData, rolesData] = await Promise.all([
                    getOrganizations(),
                    getRoles().catch(() => [])
                ]);

                if (!isMounted) return;

                setOrganizations(orgsData);
                setRoles(rolesData);

                if (orgsData.length > 0 && !selectedOrg) {
                    setSelectedOrg(orgsData[0]);
                }
            } catch (error) {
                console.error("Error al cargar datos iniciales", error);
            } finally {
                if (isMounted) setLoading(false);
            }
        };

        if (organizations.length === 0) {
            void fetchInitialData();
        } else {
            setLoading(false);
        }

        return () => {
            isMounted = false;
        };
    }, []);

    // Sincronización eficiente usando Promise.all para realizar peticiones concurrentes
    const syncDetails = async (org: Organization, forceRefresh = false) => {
        // Si ya tenemos los datos en caché y no se fuerza la recarga, evitamos llamadas innecesarias
        if (orgDetails[org.id] && !forceRefresh) return;

        try {
            const [deptData, membersData] = await Promise.all([
                getDepartments(org.id).catch(() => []),
                getOrganizationMembers(org.id).catch(() => [])
            ]);

            const defaultDeptId = deptData.length > 0 ? deptData[0].id : null;

            setOrgDetails((prev) => ({
                ...prev,
                [org.id]: {
                    departments: deptData,
                    roles: roles,
                    members: membersData,
                    departmentMembers: prev[org.id]?.departmentMembers ?? {},
                    activeDeptId: prev[org.id]?.activeDeptId ?? defaultDeptId,
                },
            }));

            if (deptData.length > 0) {
                const firstDept = deptData[0];
                setActiveDept(firstDept);
                if (!orgDetails[org.id]?.departmentMembers?.[firstDept.id]) {
                    void loadDepartmentMembers(org.id, firstDept.id);
                }
            } else {
                setActiveDept(null);
            }
        } catch (error) {
            console.error("Error en syncDetails:", error);
        } 
    };

    const loadDepartmentMembers = async (orgId: string, departmentId: string) => {
        try {
            const members = await DepartmentService.members(departmentId);
            
            setOrgDetails((prev) => ({
                ...prev,
                [orgId]: {
                    ...(prev[orgId] ?? { departments: [], roles: [], members: [], departmentMembers: {}, activeDeptId: null }),
                    departmentMembers: {
                        ...(prev[orgId]?.departmentMembers ?? {}),
                        [departmentId]: members,
                    },
                },
            }));
        } catch (error) {
            console.error("Error cargando miembros del departamento", error);
        }
    };

    const handleSelectDepartmentForOrg = async (org: Organization, dept: Department) => {
        setSelectedOrg(org);
        setActiveDept(dept);
        setOrgDetails((prev) => ({
            ...prev,
            [org.id]: {
                ...(prev[org.id] ?? { departments: [], roles: [], members: [], departmentMembers: {}, activeDeptId: null }),
                activeDeptId: dept.id,
            },
        }));

        if (!orgDetails[org.id]?.departmentMembers?.[dept.id]) {
            await loadDepartmentMembers(org.id, dept.id);
        }
    };

    const handleToggleOrganization = async (org: Organization) => {
        if (expandedOrgId === org.id) {
            setExpandedOrgId(null);
            return;
        }

        setExpandedOrgId(org.id);
        setSelectedOrg(org);
        await syncDetails(org);
    };

    const handleSelectOrganization = async (org: Organization) => {
        setSelectedOrg(org);
        setExpandedOrgId(org.id);
        await syncDetails(org, true); // Fuerza actualización si el usuario lo solicita explícitamente
    };

    const handleCreateDepartment = async (event: FormEvent) => {
        event.preventDefault();
        if (!selectedOrg) return;

        setSubmittingDepartment(true);
        try {
            await createDepartment({
                organization_id: selectedOrg.id,
                name: departmentName,
                description: departmentDescription,
            });

            setDepartmentName("");
            setDepartmentDescription("");
            setShowDeptModal(false);
            await syncDetails(selectedOrg, true);
        } catch (error) {
            console.error("Error al crear el departamento", error);
        } finally {
            setSubmittingDepartment(false);
        }
    };

    const handleAddMember = async (event: FormEvent) => {
        event.preventDefault();
        if (!activeDept || !selectedUserEmail || !selectedOrg) return;

        setSubmittingMember(true);
        try {
            await addDepartmentMember(activeDept.id, { 
                email: selectedUserEmail,
                role_id: selectedRoleId || undefined
            });

            setSelectedUserEmail("");
            setSelectedRoleId("");
            setShowMemberModal(false);
            
            await loadDepartmentMembers(selectedOrg.id, activeDept.id);
        } catch (error: any) {
            console.error("Error al añadir el miembro al departamento", error);
            alert(error.response?.data?.detail || "No se pudo añadir al usuario. Verifica que el correo electrónico pertenezca a un usuario registrado en la plataforma.");
        } finally {
            setSubmittingMember(false);
        }
    };

    const handleDeactivate = async (org?: Organization) => {
        const targetOrg = org ?? selectedOrg;
        if (!targetOrg) return;

        const confirm = window.confirm(`¿Seguro que deseas desactivar ${targetOrg.name}?`);
        if (confirm) {
            try {
                await deleteOrganization(targetOrg.id);
                const updatedOrgs = organizations.filter((orgItem) => orgItem.id !== targetOrg.id);
                setOrganizations(updatedOrgs);
                setSelectedOrg(updatedOrgs.length > 0 ? updatedOrgs[0] : null);
                if (expandedOrgId === targetOrg.id) {
                    setExpandedOrgId(null);
                }
            } catch (error) {
                console.error("Error al eliminar organización", error);
            }
        }
    };

    if (loading) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gray-50">
                <div className="animate-pulse font-medium text-emerald-600">Sincronizando Workspace Multi-tenant...</div>
            </div>
        );
    }

    return (
        <div className="flex min-h-screen flex-col gap-6 bg-gray-50 p-4 md:p-8 overflow-x-hidden w-full">
            <div className="flex items-center justify-between">
                <div>
                    <h4 className="mb-1 text-xs font-bold uppercase tracking-wider text-emerald-600">Workspace</h4>
                    <h1 className="text-3xl font-extrabold text-slate-900">Configuración Organizacional y Roles</h1>
                </div>
            </div>

            <div className="flex flex-col gap-4">
                {organizations.length > 0 ? (
                    organizations.map((org) => {
                        const summary = orgDetails[org.id];
                        const orgDepartments = summary?.departments ?? [];
                        const deptCount = orgDepartments.length;
                        const roleCount = roles.length;
                        const memberCount = summary?.members.length ?? 0;
                        const isExpanded = expandedOrgId === org.id;
                        const isSelected = selectedOrg?.id === org.id;
                        const activeDeptForOrg = summary?.activeDeptId
                            ? orgDepartments.find((dept) => dept.id === summary.activeDeptId) ?? null
                            : (orgDepartments.length > 0 ? orgDepartments[0] : null);
                        const currentMembers = activeDeptForOrg ? (summary?.departmentMembers[activeDeptForOrg.id] ?? []) : [];

                        return (
                            <div key={org.id} className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
                                <button
                                    onClick={() => void handleToggleOrganization(org)}
                                    className="flex w-full items-start justify-between gap-4 text-left"
                                >
                                    <div>
                                        <h2 className="text-xl font-bold text-slate-800">{org.name}</h2>
                                        <p className="mt-1 text-sm text-gray-500">{org.description || "Sin descripción proporcionada."}</p>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-emerald-600">
                                            {org.status || "Active"}
                                        </span>
                                        <span className="text-sm text-gray-400">{isExpanded ? "▲" : "▼"}</span>
                                    </div>
                                </button>

                                {isExpanded && (
                                    <div className="mt-6 space-y-6">
                                        <div className="flex flex-wrap gap-3 border-b border-gray-100 pb-5">
                                            <button
                                                onClick={(event) => {
                                                    event.stopPropagation();
                                                    void handleSelectOrganization(org);
                                                }}
                                                className="rounded-xl bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-emerald-700"
                                            >
                                                Sincronizar detalles
                                            </button>
                                            <button
                                                onClick={(event) => {
                                                    event.stopPropagation();
                                                    setSelectedOrg(org);
                                                    setShowDeptModal(true);
                                                }}
                                                className="rounded-xl border border-gray-200 bg-white px-4 py-1.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
                                            >
                                                + Departamento
                                            </button>
                                            <button
                                                onClick={(event) => {
                                                    event.stopPropagation();
                                                    setSelectedOrg(org);
                                                    if (orgDepartments.length > 0 && !activeDept) {
                                                        setActiveDept(orgDepartments[0]);
                                                    }
                                                    setShowMemberModal(true);
                                                }}
                                                className="rounded-xl border border-gray-200 bg-white px-4 py-1.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
                                            >
                                                + Añadir Miembro
                                            </button>
                                            <button
                                                onClick={(event) => {
                                                    event.stopPropagation();
                                                    void handleDeactivate(org);
                                                }}
                                                className="ml-auto rounded-xl border border-red-200 bg-red-50 px-4 py-1.5 text-sm font-medium text-red-600 transition-colors hover:bg-red-100"
                                            >
                                                Desactivar
                                            </button>
                                        </div>

                                        <div className="flex flex-wrap gap-2 text-xs">
                                            <span className="rounded-full bg-gray-100 px-2.5 py-1">{deptCount} departamentos</span>
                                            <span className="rounded-full bg-gray-100 px-2.5 py-1">{roleCount} roles</span>
                                            <span className="rounded-full bg-gray-100 px-2.5 py-1">{memberCount} miembros</span>
                                        </div>

                                        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-start">
                                            <div className="flex flex-col gap-3 lg:col-span-5 min-w-0">
                                                <div className="flex items-center justify-between">
                                                    <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400">Departamentos</h3>
                                                    <span className="text-xs text-gray-400">{orgDepartments.length} totales</span>
                                                </div>
                                                <div className="flex flex-col gap-2">
                                                    {orgDepartments.length > 0 ? (
                                                        orgDepartments.map((dept) => (
                                                            <div
                                                                key={dept.id}
                                                                onClick={() => void handleSelectDepartmentForOrg(org, dept)}
                                                                className={`cursor-pointer rounded-xl border p-4 transition-all ${
                                                                    isSelected && activeDeptForOrg?.id === dept.id
                                                                        ? "border-emerald-500 bg-emerald-50/40 shadow-xs"
                                                                        : "border-gray-100 hover:bg-gray-50"
                                                                }`}
                                                            >
                                                                <div className="flex items-start justify-between gap-2">
                                                                    <div>
                                                                        <h4 className="text-sm font-bold text-gray-800">{dept.name}</h4>
                                                                        <p className="mt-0.5 text-xs text-gray-400">{dept.description}</p>
                                                                    </div>
                                                                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                                                                        {dept.members ?? 0} miembros
                                                                    </span>
                                                                </div>
                                                            </div>
                                                        ))
                                                    ) : (
                                                        <div className="rounded-xl border border-dashed border-gray-200 p-4 text-center text-xs text-gray-400">
                                                            No hay departamentos registrados.
                                                        </div>
                                                    )}
                                                </div>
                                            </div>

                                            <div className="flex flex-col gap-3 lg:col-span-7">
                                                <div className="flex items-center justify-between">
                                                    <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400">
                                                        Miembros de: <span className="font-bold normal-case text-emerald-600">{activeDeptForOrg ? activeDeptForOrg.name : "Ninguno"}</span>
                                                    </h3>
                                                    {activeDeptForOrg && (
                                                        <button
                                                            onClick={(event) => {
                                                                event.stopPropagation();
                                                                setSelectedOrg(org);
                                                                setActiveDept(activeDeptForOrg);
                                                                setShowMemberModal(true);
                                                            }}
                                                            className="text-sm font-semibold text-emerald-600 hover:underline"
                                                        >
                                                            + Añadir
                                                        </button>
                                                    )}
                                                </div>
                                                <div className="overflow-hidden rounded-xl border border-gray-100 bg-white">
                                                    {activeDeptForOrg ? (
                                                        currentMembers.length > 0 ? (
                                                            currentMembers.map((member) => (
                                                                <div key={member.id} className="flex items-center justify-between border-b border-gray-100 p-4 last:border-0 hover:bg-gray-50/60">
                                                                    <div>
                                                                        <h4 className="text-sm font-semibold text-gray-800">{member.name}</h4>
                                                                        <p className="text-xs text-gray-400 truncate">{member.email}</p>
                                                                    </div>
                                                                    <span className="rounded-lg border border-slate-200 bg-slate-100/80 px-2.5 py-1 text-xs font-medium text-slate-600">
                                                                        {member.role ?? "user"}
                                                                    </span>
                                                                </div>
                                                            ))
                                                        ) : (
                                                            <div className="p-8 text-center text-xs text-gray-400">No hay miembros en este departamento.</div>
                                                        )
                                                    ) : (
                                                        <div className="p-8 text-center text-xs text-gray-400">Selecciona un departamento para ver sus miembros.</div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })
                ) : (
                    <div className="rounded-xl border border-dashed p-4 text-sm text-gray-400">
                        No hay organizaciones registradas.
                    </div>
                )}
            </div>

            {showDeptModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
                    <div className="w-full max-w-md rounded-xl border border-gray-100 bg-white p-6 shadow-xl">
                        <h3 className="mb-4 text-xl font-bold text-slate-900">Nuevo departamento</h3>
                        <form onSubmit={handleCreateDepartment} className="flex flex-col gap-4">
                            <div>
                                <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-gray-500">Nombre</label>
                                <input
                                    required
                                    value={departmentName}
                                    onChange={(e) => setDepartmentName(e.target.value)}
                                    className="w-full rounded-lg border border-gray-200 p-2.5 text-sm outline-emerald-500"
                                    placeholder="Ej. Logística y Calidad"
                                />
                            </div>
                            <div>
                                <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-gray-500">Descripción</label>
                                <textarea
                                    value={departmentDescription}
                                    onChange={(e) => setDepartmentDescription(e.target.value)}
                                    className="w-full rounded-lg border border-gray-200 p-2.5 text-sm outline-emerald-500"
                                    rows={3}
                                    placeholder="Describe el propósito del departamento"
                                />
                            </div>
                            <div className="flex justify-end gap-2">
                                <button type="button" onClick={() => setShowDeptModal(false)} className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50">
                                    Cancelar
                                </button>
                                <button type="submit" disabled={submittingDepartment} className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50">
                                    {submittingDepartment ? "Creando..." : "Crear departamento"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {showMemberModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
                    <div className="w-full max-w-md rounded-xl border border-gray-100 bg-white p-6 shadow-xl">
                        <h3 className="mb-4 text-xl font-bold text-slate-900">Añadir miembro al departamento</h3>
                        <form onSubmit={handleAddMember} className="flex flex-col gap-4">
                            <div>
                                <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-gray-500">Departamento activo</label>
                                <input
                                    readOnly
                                    value={activeDept?.name ?? "Selecciona un departamento"}
                                    className="w-full rounded-lg border border-gray-200 bg-gray-50 p-2.5 text-sm"
                                />
                            </div>
                            
                            <div>
                                <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-gray-500">
                                    Correo del Usuario (Registrado)
                                </label>
                                <input
                                    type="email"
                                    required
                                    value={selectedUserEmail}
                                    onChange={(e) => setSelectedUserEmail(e.target.value)}
                                    className="w-full rounded-lg border border-gray-200 p-2.5 text-sm outline-emerald-500"
                                    placeholder="ejemplo@correo.com"
                                />
                                <p className="mt-1 text-[11px] text-gray-400">
                                    * El usuario debe estar previamente registrado en la plataforma global para ser añadido.
                                </p>
                            </div>

                            <div>
                                <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-gray-500">
                                    Rol Organizacional (Contexto RAG)
                                </label>
                                <select
                                    value={selectedRoleId}
                                    onChange={(e) => setSelectedRoleId(e.target.value)}
                                    className="w-full rounded-lg border border-gray-200 p-2.5 text-sm outline-emerald-500 font-medium"
                                    required
                                >
                                    <option value="">Selecciona el rol y alcance...</option>
                                    {roles.map((role) => {
                                        const roleDef = ROLE_DEFINITIONS[role.name] || { 
                                            label: role.name, 
                                            context: role.description || "Sin contexto RAG asignado" 
                                        };

                                        return (
                                            <option key={role.id} value={role.id}>
                                                {roleDef.label} — [{roleDef.context}]
                                            </option>
                                        );
                                    })}
                                </select>
                                <p className="mt-1 text-[11px] text-gray-400">
                                    * El rol seleccionado define los metadatos de filtrado para las consultas del Asistente IA.
                                </p>
                            </div>
                            
                            <div className="flex justify-end gap-2 mt-2">
                                <button type="button" onClick={() => setShowMemberModal(false)} className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50">
                                    Cancelar
                                </button>
                                <button type="submit" disabled={submittingMember} className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50">
                                    {submittingMember ? "Guardando..." : "Añadir miembro"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}