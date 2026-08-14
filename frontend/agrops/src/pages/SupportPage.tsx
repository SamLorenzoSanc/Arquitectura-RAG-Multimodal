import { useEffect, useState, type FormEvent } from "react";
import { useOrganization } from "@/context/OrganizationContext";
import AccountService, {
  type OrgAdmin,
  type SupportTicket,
} from "@/services/account.service";

function formatDate(value?: string) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("es-ES", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function SupportPage() {
  const { selectedOrg } = useOrganization();
  const [admins, setAdmins] = useState<OrgAdmin[]>([]);
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [isAdmin, setIsAdmin] = useState(false);
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const load = async () => {
    try {
      const [adminList, inbox] = await Promise.all([
        AccountService.admins(selectedOrg?.id),
        AccountService.supportTickets(),
      ]);
      setAdmins(adminList);
      setTickets(inbox.tickets);
      setIsAdmin(inbox.is_admin);
    } catch {
      setAdmins([]);
      setTickets([]);
    }
  };

  useEffect(() => {
    void load();
  }, [selectedOrg?.id]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSending(true);
    setError(null);
    setStatus(null);
    try {
      await AccountService.createTicket({
        subject,
        message,
        organization_id: selectedOrg?.id,
      });
      setSubject("");
      setMessage("");
      setStatus("Mensaje enviado a los administradores.");
      await load();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        .response?.data?.detail;
      setError(detail || "No se pudo enviar el mensaje.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-[1.1fr_0.9fr]">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-lg font-bold text-slate-900">Soporte</h1>
        <p className="mt-1 text-sm text-slate-500">
          Escribe a los administradores de la aplicación. Recibirán tu aviso
          {admins.length
            ? `: ${admins.map((admin) => admin.name).join(", ")}`
            : " en cuanto esté disponible un administrador de tu organización"}
          .
        </p>
        <form onSubmit={(event) => void handleSubmit(event)} className="mt-5 space-y-3">
          <input
            required
            minLength={4}
            value={subject}
            onChange={(event) => setSubject(event.target.value)}
            placeholder="Asunto"
            className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
          />
          <textarea
            required
            minLength={10}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Describe el problema o la duda…"
            rows={7}
            className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
          />
          {error && <p className="text-xs text-red-600">{error}</p>}
          {status && <p className="text-xs text-emerald-700">{status}</p>}
          <button
            type="submit"
            disabled={sending}
            className="rounded-lg bg-[color:var(--agro-primary)] px-4 py-2 text-xs font-bold text-white disabled:opacity-50"
          >
            {sending ? "Enviando…" : "Enviar a administradores"}
          </button>
        </form>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-sm font-bold text-slate-800">
          {isAdmin ? "Bandeja de administradores" : "Tus mensajes"}
        </h2>
        <div className="mt-3 space-y-3">
          {tickets.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-400">
              Todavía no hay mensajes.
            </p>
          ) : (
            tickets.map((ticket) => (
              <article
                key={ticket.id}
                className="rounded-xl border border-slate-100 bg-slate-50 p-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-semibold text-slate-800">
                    {ticket.subject}
                  </p>
                  <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-bold uppercase text-blue-700">
                    {ticket.status}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {ticket.author_name} · {formatDate(ticket.created_at)}
                </p>
                <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">
                  {ticket.message}
                </p>
              </article>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
