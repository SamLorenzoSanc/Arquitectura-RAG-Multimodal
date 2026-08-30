export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export type ApiEndpoint = {
  method: HttpMethod;
  path: string;
  tag: string;
  summary: string;
  auth: boolean;
  query?: string[];
  body?: Record<string, unknown> | string;
  response?: Record<string, unknown> | string;
};

export const API_BASE = "/api/v1";

export const API_CONVENTIONS = [
  "Prefijo estable: todas las rutas van bajo /api/v1.",
  "JSON UTF-8 en cuerpo (Content-Type: application/json), salvo subida de documentos (multipart/form-data).",
  "Autenticación: cabecera Authorization: Bearer <access_token> en todas las rutas salvo /auth/register y /auth/login.",
  "Identificadores en UUID. Fechas en ISO-8601.",
  "Errores: { \"detail\": \"mensaje\" } con código HTTP 4xx/5xx.",
];

export const HEXAGON_LAYERS = [
  {
    name: "Adaptadores de entrada",
    path: "gateway/<contexto>/adapters/inbound/",
    detail: "Routers FastAPI. Reciben HTTP, validan el cuerpo y llaman a aplicación.",
  },
  {
    name: "Aplicación y dominio",
    path: "gateway/<contexto>/application/ · domain/",
    detail: "Casos de uso y puertos. Sin FastAPI ni SQL.",
  },
  {
    name: "Adaptadores de salida",
    path: "gateway/<contexto>/adapters/outbound/",
    detail: "PostgreSQL, JWT, hasher, almacenamiento de ficheros.",
  },
  {
    name: "Composition root",
    path: "gateway/<contexto>/composition.py y gateway/main.py",
    detail: "Ensambla el hexágono y monta los routers en /api/v1.",
  },
];

export const API_ENDPOINTS: ApiEndpoint[] = [
  {
    method: "POST",
    path: "/auth/register",
    tag: "Authentication",
    summary: "Crear cuenta",
    auth: false,
    body: { name: "Ana Pérez", email: "ana@cooperativa.es", password: "********" },
    response: { id: "<uuid>", email: "ana@cooperativa.es" },
  },
  {
    method: "POST",
    path: "/auth/login",
    tag: "Authentication",
    summary: "Obtener token de sesión",
    auth: false,
    body: { email: "ana@cooperativa.es", password: "********" },
    response: { access_token: "<jwt>", token_type: "Bearer", expires_in: 3600 },
  },
  {
    method: "GET",
    path: "/auth/me",
    tag: "Authentication",
    summary: "Usuario de la sesión actual",
    auth: true,
  },
  {
    method: "POST",
    path: "/auth/logout",
    tag: "Authentication",
    summary: "Cerrar sesión",
    auth: true,
  },
  {
    method: "GET",
    path: "/health",
    tag: "Health",
    summary: "Salud del gateway",
    auth: false,
  },
  {
    method: "GET",
    path: "/health/ready",
    tag: "Health",
    summary: "Listo para tráfico (dependencias)",
    auth: false,
  },
  {
    method: "GET",
    path: "/knowledge/",
    tag: "Knowledge",
    summary: "Listar bases de conocimiento",
    auth: true,
    query: ["organization_id?", "department_id?"],
  },
  {
    method: "GET",
    path: "/knowledge/current",
    tag: "Knowledge",
    summary: "Base de conocimiento activa",
    auth: true,
    query: ["organization_id?"],
  },
  {
    method: "GET",
    path: "/knowledge/{knowledge_base_id}",
    tag: "Knowledge",
    summary: "Detalle de un proyecto / base de conocimiento",
    auth: true,
    query: ["organization_id?"],
  },
  {
    method: "POST",
    path: "/knowledge/",
    tag: "Knowledge",
    summary: "Crear base de conocimiento",
    auth: true,
    body: { name: "demo_agrops", description: "Consulta normativa con RAG", use_case: "Q/A" },
  },
  {
    method: "PATCH",
    path: "/knowledge/{knowledge_base_id}",
    tag: "Knowledge",
    summary: "Actualizar nombre, descripción o caso de uso de un proyecto",
    auth: true,
    query: ["organization_id?"],
    body: { name: "sanidad_platano", use_case: "Sanidad vegetal", description: "Protocolos de plagas" },
  },
  {
    method: "DELETE",
    path: "/knowledge/{knowledge_base_id}",
    tag: "Knowledge",
    summary: "Eliminar un proyecto y su documentación",
    auth: true,
    query: ["organization_id?"],
  },
  {
    method: "GET",
    path: "/documents",
    tag: "Documents",
    summary: "Listar documentos del corpus",
    auth: true,
    query: ["knowledge_base_id"],
  },
  {
    method: "POST",
    path: "/documents",
    tag: "Documents",
    summary: "Subir e ingerir un documento (chunks + embeddings)",
    auth: true,
    body: "multipart/form-data: file, knowledge_base_id, title?, description?",
  },
  {
    method: "DELETE",
    path: "/documents/{document_id}",
    tag: "Documents",
    summary: "Eliminar documento",
    auth: true,
    query: ["knowledge_base_id"],
  },
  {
    method: "POST",
    path: "/chat/",
    tag: "Chat",
    summary: "Preguntar al RAG agéntico (inferencia)",
    auth: true,
    body: {
      question: "¿Qué requisitos POSEI aplica al plátano?",
      conversation_id: null,
      history: [{ role: "user", content: "…" }],
      organization_id: "<uuid>",
      organization_name: "Cooperativa Norte",
      knowledge_base_id: "<uuid?>",
      department_id: "<uuid?>",
      use_rag: true,
      rag_mode: "agentic",
      model: "llama3.2:latest",
    },
    response: {
      conversation_id: "<uuid>",
      answer: "Según el documento…",
      context: [{ type: "chunk", page_content: "…", metadata: { source: "posei.pdf" } }],
      related_questions: ["¿Y el plazo de solicitud?"],
    },
  },
  {
    method: "POST",
    path: "/chat/stream",
    tag: "Chat",
    summary: "Chat con SSE: proceso del agente + tokens en tiempo real",
    auth: true,
    body: {
      question: "¿Qué requisitos POSEI aplica al plátano?",
      use_rag: true,
      rag_mode: "agentic",
      model: "llama3.2:latest",
    },
    response: {
      note: "text/event-stream con eventos meta|status|intent|plan|tool_*|grade|token|done|error",
    },
  },
  {
    method: "GET",
    path: "/chat/conversations",
    tag: "Chat",
    summary: "Historial de conversaciones",
    auth: true,
  },
  {
    method: "GET",
    path: "/chat/{conversation_id}",
    tag: "Chat",
    summary: "Detalle de una conversación",
    auth: true,
  },
  {
    method: "DELETE",
    path: "/chat/{conversation_id}",
    tag: "Chat",
    summary: "Borrar conversación",
    auth: true,
  },
  {
    method: "POST",
    path: "/organization",
    tag: "Organization",
    summary: "Crear organización (tenant, KB inicial y rol admin)",
    auth: true,
    body: { name: "Cooperativa Norte", description: "Gran Canaria · plátano" },
    response: {
      status: "success",
      organization_id: "<uuid>",
      tenant_id: "<uuid>",
      default_knowledge_base_id: "<uuid>",
    },
  },
  {
    method: "GET",
    path: "/organization",
    tag: "Organization",
    summary: "Listar organizaciones del usuario",
    auth: true,
  },
  {
    method: "GET",
    path: "/organization/{organization_id}",
    tag: "Organization",
    summary: "Detalle de organización",
    auth: true,
  },
  {
    method: "GET",
    path: "/organization/{organization_id}/members",
    tag: "Organization",
    summary: "Miembros de la organización",
    auth: true,
  },
  {
    method: "GET",
    path: "/organization/{organization_id}/departments",
    tag: "Organization",
    summary: "Departamentos de la organización",
    auth: true,
  },
  {
    method: "DELETE",
    path: "/organization/{organization_id}",
    tag: "Organization",
    summary: "Eliminar organización",
    auth: true,
  },
  {
    method: "POST",
    path: "/department",
    tag: "Department",
    summary: "Crear departamento",
    auth: true,
    body: {
      organization_id: "<uuid>",
      name: "Sanidad vegetal",
      description: "Plagas y tratamientos",
    },
  },
  {
    method: "GET",
    path: "/department/organization/{organization_id}",
    tag: "Department",
    summary: "Departamentos por organización",
    auth: true,
  },
  {
    method: "POST",
    path: "/department/{department_id}/members",
    tag: "Department",
    summary: "Añadir miembro por correo (debe estar registrado)",
    auth: true,
    body: { email: "tecnico@cooperativa.es", role_id: "<uuid?>" },
  },
  {
    method: "GET",
    path: "/department/{department_id}/members",
    tag: "Department",
    summary: "Miembros del departamento",
    auth: true,
  },
  {
    method: "DELETE",
    path: "/department/{department_id}/members/{user_id}",
    tag: "Department",
    summary: "Quitar miembro",
    auth: true,
  },
  {
    method: "GET",
    path: "/account/profile",
    tag: "Account",
    summary: "Leer perfil y foto",
    auth: true,
    query: ["user_id?", "organization_id?"],
  },
  {
    method: "PATCH",
    path: "/account/profile",
    tag: "Account",
    summary: "Actualizar perfil",
    auth: true,
    body: {
      name: "Ana Pérez",
      job_title: "Técnica de calidad",
      phone: "+34 600 000 000",
      island: "Tenerife",
      municipality: "Guía de Isora",
      crop_focus: "Plátano",
      bio: "…",
      preferred_language: "es",
      notify_email: true,
      notify_whatsapp: false,
    },
  },
  {
    method: "POST",
    path: "/account/profile/avatar",
    tag: "Account",
    summary: "Subir foto de perfil (JPG, PNG o WEBP, máx. 2 MB)",
    auth: true,
    body: "multipart/form-data: file",
  },
  {
    method: "POST",
    path: "/account/tokens",
    tag: "Account",
    summary: "Generar Access Key / API key",
    auth: true,
    body: { name: "Integración PAC", kind: "access", expires_days: 30 },
    response: {
      token: "<jwt>",
      prefix: "agro_a1b2c3d4",
      token_type: "Bearer",
      note: "Copia el token ahora. No se volverá a mostrar.",
    },
  },
  {
    method: "GET",
    path: "/account/tokens",
    tag: "Account",
    summary: "Listar claves",
    auth: true,
    query: ["kind?=access|api_key"],
  },
  {
    method: "DELETE",
    path: "/account/tokens/{token_id}",
    tag: "Account",
    summary: "Revocar clave",
    auth: true,
  },
  {
    method: "GET",
    path: "/account/usage",
    tag: "Account",
    summary: "Uso de la cuenta",
    auth: true,
  },
  {
    method: "GET",
    path: "/account/analytics",
    tag: "Account",
    summary: "Analíticas globales del usuario (totales, actividad y últimas acciones)",
    auth: true,
    query: ["user_id?", "organization_id?"],
  },
  {
    method: "GET",
    path: "/account/users",
    tag: "Account",
    summary: "Usuarios gestionados de la organización",
    auth: true,
    query: ["organization_id", "q?", "limit?", "offset?"],
  },
  {
    method: "GET",
    path: "/account/projects",
    tag: "Account",
    summary: "Proyectos (KB) de un usuario",
    auth: true,
    query: ["organization_id", "user_id?"],
  },
  {
    method: "GET",
    path: "/account/support",
    tag: "Account",
    summary: "Tickets de soporte",
    auth: true,
  },
  {
    method: "POST",
    path: "/account/support",
    tag: "Account",
    summary: "Crear ticket",
    auth: true,
    body: {
      subject: "Fallo al indexar PDF",
      message: "Al subir el boletín…",
      organization_id: "<uuid?>",
    },
  },
  {
    method: "GET",
    path: "/users/roles",
    tag: "Users",
    summary: "Catálogo de roles",
    auth: true,
  },
  {
    method: "GET",
    path: "/users/me/roles",
    tag: "Users",
    summary: "Roles del usuario autenticado",
    auth: true,
  },
];

export function openApiUrls(): string[] {
  const api = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
  const origin = String(api).replace(/\/api\/v1\/?$/, "");
  return ["/openapi.json", `${origin}/openapi.json`];
}

export async function fetchOpenApi(): Promise<{
  title?: string;
  version?: string;
  paths: number;
} | null> {
  for (const url of openApiUrls()) {
    try {
      const response = await fetch(url, { headers: { Accept: "application/json" } });
      if (!response.ok) continue;
      const spec = await response.json();
      return {
        title: spec.info?.title,
        version: spec.info?.version,
        paths: Object.keys(spec.paths ?? {}).length,
      };
    } catch {
      /* probar siguiente */
    }
  }
  return null;
}
