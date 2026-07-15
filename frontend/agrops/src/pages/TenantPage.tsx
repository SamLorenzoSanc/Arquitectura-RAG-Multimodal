"use client";

import { useEffect, useState } from "react";

import TenantService from "@/services/tenant.service";

import type {
    Tenant,
    CreateTenantRequest,
    UpdateTenantRequest,
} from "@/types/tenant";

export default function TenantPage() {

    const [tenants, setTenants] = useState<Tenant[]>([]);

    const [loading, setLoading] = useState(true);

    const [error, setError] = useState<string | null>(null);

    const [showModal, setShowModal] = useState(false);

    const [editingTenant, setEditingTenant] =
        useState<Tenant | null>(null);

    const [saving, setSaving] = useState(false);

    const [form, setForm] = useState<CreateTenantRequest>({
        name: "",
        description: "",
    });

    async function loadTenants() {
        
        try {
        
            console.log("Cargando tenants...");
        
            setLoading(true);
        
            setError(null);
        
            const data = await TenantService.list();
        
            console.log("Respuesta:", data);
        
            setTenants(data);
        
        } catch (err) {
        
            console.error("Error cargando tenants:", err);
        
            setError("No se pudieron cargar los tenants.");
        
        } finally {
        
            setLoading(false);
        
        }
    
    }

    useEffect(() => {

        loadTenants();

    }, []);

    function openCreateModal() {

        setEditingTenant(null);

        setForm({

            name: "",

            description: "",

        });

        setShowModal(true);

    }

    function openEditModal(
        tenant: Tenant,
    ) {

        setEditingTenant(tenant);

        setForm({

            name: tenant.name,

            description: tenant.description ?? "",

        });

        setShowModal(true);

    }

    function closeModal() {

        setShowModal(false);

        setEditingTenant(null);

    }

    // ===============================
    // Actualizar formulario
    // ===============================

    function updateField(
        field: keyof CreateTenantRequest,
        value: string,
    ) {

        setForm((previous) => ({

            ...previous,

            [field]: value,

        }));

    }

    // ===============================
    // Guardar (Crear / Editar)
    // ===============================

    async function saveTenant() {

        try {

            setSaving(true);

            if (editingTenant == null) {

                await TenantService.create(form);

            } else {

                const request: UpdateTenantRequest = {

                    name: form.name,

                    description: form.description,

                };

                await TenantService.update(

                    editingTenant.id,

                    request,

                );

            }

            closeModal();

            await loadTenants();

        } catch (err) {

            console.error(err);

            alert("No se pudo guardar el tenant.");

        } finally {

            setSaving(false);

        }

    }

    async function deleteTenant(
        tenant: Tenant,
    ) {

        const confirmed = confirm(

            `¿Eliminar el tenant "${tenant.name}"?`

        );

        if (!confirmed)
            return;

        try {

            await TenantService.delete(tenant.id);

            await loadTenants();

        } catch (err) {

            console.error(err);

            alert("No se pudo eliminar.");

        }

    }

    async function toggleActive(
        tenant: Tenant,
    ) {

        try {

            if (tenant.active) {

                await TenantService.deactivate(
                    tenant.id,
                );

            } else {

                await TenantService.activate(
                    tenant.id,
                );

            }

            await loadTenants();

        } catch (err) {

            console.error(err);

            alert("No se pudo actualizar.");

        }

    }

    // ===============================
    // Render
    // ===============================

    return (

        <div className="space-y-6">

            <div className="flex justify-between items-center">

                <div>

                    <h1 className="text-3xl font-bold">

                        Tenants

                    </h1>

                    <p className="text-gray-500">

                        Administra los espacios de trabajo.

                    </p>

                </div>

                <button
                    onClick={openCreateModal}
                    className="rounded-lg bg-green-600 px-4 py-2 text-white hover:bg-green-700"
                >
                    Nuevo Tenant
                </button>

            </div>

            {loading && (

                <div className="bg-white rounded-xl shadow p-6">

                    Cargando...

                </div>

            )}

            {error && (

                <div className="rounded-lg bg-red-100 p-4 text-red-700">

                    {error}

                </div>

            )}

            {!loading && !error && (

                <div className="bg-white rounded-xl shadow">

                    {/* Tabla */}

                </div>

            )}

            {/* Modal */}

            {showModal && (

                <div>

                    {/* Modal */}

                </div>

            )}

        </div>

    );

}