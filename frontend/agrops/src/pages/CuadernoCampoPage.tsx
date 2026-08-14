"use client";

import { useMemo, useState, type FormEvent } from "react";
import {
  BookOpen,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Clock,
  Loader2,
  Pencil,
  Plus,
  Trash2,
} from "lucide-react";
import { useOrganization } from "@/context/OrganizationContext";
import {
  useCreateNotebookEntry,
  useDeleteNotebookEntry,
  useFieldNotebook,
  useUpdateNotebookEntry,
} from "@/hooks/useCachedApi";
import {
  NOTEBOOK_CATEGORIES,
  type FieldNotebookEntry,
  type NotebookCategory,
} from "@/services/notebook.service";

const WEEKDAYS = ["L", "M", "X", "J", "V", "S", "D"];

const CATEGORY_STYLE: Record<NotebookCategory, string> = {
  riego: "bg-sky-100 text-sky-800",
  plaga: "bg-amber-100 text-amber-800",
  fertilizacion: "bg-lime-100 text-lime-800",
  cosecha: "bg-emerald-100 text-emerald-800",
  clima: "bg-indigo-100 text-indigo-800",
  maquinaria: "bg-slate-200 text-slate-800",
  otro: "bg-blue-100 text-blue-800",
};

function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function parseISODate(value: string): Date {
  const [y, m, d] = value.split("-").map(Number);
  return new Date(y, (m || 1) - 1, d || 1);
}

function monthLabel(d: Date): string {
  return d.toLocaleDateString("es-ES", { month: "long", year: "numeric" });
}

function dayLabel(iso: string): string {
  return parseISODate(iso).toLocaleDateString("es-ES", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

function monthGrid(cursor: Date): Array<{ iso: string; inMonth: boolean }> {
  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const first = new Date(year, month, 1);
  const startOffset = (first.getDay() + 6) % 7;
  const start = new Date(year, month, 1 - startOffset);
  return Array.from({ length: 42 }, (_, i) => {
    const day = new Date(start);
    day.setDate(start.getDate() + i);
    return { iso: toISODate(day), inMonth: day.getMonth() === month };
  });
}

function categoryLabel(id: string): string {
  return NOTEBOOK_CATEGORIES.find((c) => c.id === id)?.label ?? id;
}

function reminderTime(value?: string | null): string {
  if (!value) return "";
  const match = value.match(/T(\d{2}:\d{2})/);
  return match?.[1] ?? "";
}

export default function CuadernoCampoPage() {
  const { selectedOrg } = useOrganization();
  const today = toISODate(new Date());
  const [cursor, setCursor] = useState(() => new Date());
  const [selectedDate, setSelectedDate] = useState(today);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [category, setCategory] = useState<NotebookCategory>("otro");
  const [reminder, setReminder] = useState("");
  const [error, setError] = useState<string | null>(null);

  const monthStart = toISODate(new Date(cursor.getFullYear(), cursor.getMonth(), 1));
  const monthEnd = toISODate(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0));
  const { data: entries = [], isLoading } = useFieldNotebook(
    selectedOrg?.id,
    monthStart,
    monthEnd,
  );
  const createEntry = useCreateNotebookEntry();
  const updateEntry = useUpdateNotebookEntry();
  const deleteEntry = useDeleteNotebookEntry();

  const days = useMemo(() => monthGrid(cursor), [cursor]);
  const counts = useMemo(() => {
    const map = new Map<string, number>();
    for (const entry of entries) {
      const key = entry.entry_date.slice(0, 10);
      map.set(key, (map.get(key) ?? 0) + 1);
    }
    return map;
  }, [entries]);

  const dayEntries = entries.filter((e) => e.entry_date.slice(0, 10) === selectedDate);
  const upcoming = entries
    .filter((e) => e.reminder_at && e.entry_date.slice(0, 10) >= today)
    .slice(0, 5);
  const saving = createEntry.isPending || updateEntry.isPending;

  const resetForm = () => {
    setEditingId(null);
    setTitle("");
    setBody("");
    setCategory("otro");
    setReminder("");
    setError(null);
  };

  const fillForm = (entry: FieldNotebookEntry) => {
    setEditingId(entry.id);
    setTitle(entry.title);
    setBody(entry.body ?? "");
    setCategory(entry.category);
    setReminder(reminderTime(entry.reminder_at));
    setError(null);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!title.trim()) {
      setError("Pon un título a la anotación.");
      return;
    }
    const payload = {
      title: title.trim(),
      body: body.trim(),
      entry_date: selectedDate,
      category,
      crop_id: null,
      organization_id: selectedOrg?.id ?? null,
      reminder_at: reminder ? `${selectedDate}T${reminder}:00` : null,
    };
    try {
      if (editingId) {
        await updateEntry.mutateAsync({ id: editingId, payload });
      } else {
        await createEntry.mutateAsync(payload);
      }
      resetForm();
    } catch {
      setError("No se pudo guardar la anotación.");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteEntry.mutateAsync(id);
      if (editingId === id) resetForm();
    } catch {
      setError("No se pudo borrar la anotación.");
    }
  };

  return (
    <div className="min-h-screen space-y-6 bg-slate-50/50 p-8">
      <header className="rounded-2xl border border-blue-100 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold uppercase tracking-wider text-emerald-800">
            Trabajo diario
          </span>
          <span className="text-xs font-medium text-slate-400">Agenda del agricultor</span>
        </div>
        <h1 className="mt-1 flex items-center gap-2 text-2xl font-black text-blue-950">
          <BookOpen size={22} />
          Cuaderno de campo
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-600">
          Anota riegos, plagas, cosecha o lo que veas en la finca. Elige un día
          en el calendario, escribe y guarda. Puedes poner un recordatorio.
        </p>
      </header>

      <div className="grid gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
        <section className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <button
                type="button"
                onClick={() =>
                  setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))
                }
                className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100"
                aria-label="Mes anterior"
              >
                <ChevronLeft size={18} />
              </button>
              <p className="flex items-center gap-1.5 text-sm font-bold capitalize text-slate-800">
                <CalendarDays size={15} />
                {monthLabel(cursor)}
              </p>
              <button
                type="button"
                onClick={() =>
                  setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))
                }
                className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100"
                aria-label="Mes siguiente"
              >
                <ChevronRight size={18} />
              </button>
            </div>
            <div className="grid grid-cols-7 gap-1 text-center text-[11px] font-bold text-slate-400">
              {WEEKDAYS.map((d) => (
                <span key={d} className="py-1">
                  {d}
                </span>
              ))}
            </div>
            <div className="mt-1 grid grid-cols-7 gap-1">
              {days.map((day) => {
                const selected = day.iso === selectedDate;
                const isToday = day.iso === today;
                const count = counts.get(day.iso) ?? 0;
                return (
                  <button
                    key={day.iso}
                    type="button"
                    onClick={() => {
                      setSelectedDate(day.iso);
                      resetForm();
                    }}
                    className={`relative flex h-10 flex-col items-center justify-center rounded-xl text-xs font-semibold ${
                      selected
                        ? "bg-[#0038A8] text-white shadow-sm"
                        : isToday
                          ? "bg-blue-50 text-[#0038A8]"
                          : day.inMonth
                            ? "text-slate-700 hover:bg-slate-50"
                            : "text-slate-300"
                    }`}
                  >
                    {parseISODate(day.iso).getDate()}
                    {count > 0 && (
                      <span
                        className={`absolute bottom-1 h-1 w-1 rounded-full ${
                          selected ? "bg-white" : "bg-emerald-500"
                        }`}
                      />
                    )}
                  </button>
                );
              })}
            </div>
            <button
              type="button"
              onClick={() => {
                const now = new Date();
                setCursor(now);
                setSelectedDate(toISODate(now));
                resetForm();
              }}
              className="mt-3 w-full rounded-xl border border-slate-200 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50"
            >
              Ir a hoy
            </button>
          </div>

          {upcoming.length > 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="mb-2 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-slate-400">
                <Clock size={13} />
                Próximos recordatorios
              </p>
              <ul className="space-y-2">
                {upcoming.map((entry) => (
                  <li key={entry.id} className="text-sm text-slate-700">
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedDate(entry.entry_date.slice(0, 10));
                        fillForm(entry);
                      }}
                      className="w-full rounded-lg px-2 py-1.5 text-left hover:bg-slate-50"
                    >
                      <span className="font-semibold">{entry.title}</span>
                      <span className="mt-0.5 block text-[11px] text-slate-400">
                        {entry.entry_date.slice(0, 10)} · {reminderTime(entry.reminder_at)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>

        <section className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-black capitalize text-blue-950">
              {dayLabel(selectedDate)}
            </h2>
            <p className="text-xs text-slate-500">
              {dayEntries.length === 0
                ? "Aún no hay anotaciones este día."
                : `${dayEntries.length} anotación${dayEntries.length === 1 ? "" : "es"}`}
            </p>

            {isLoading ? (
              <div className="flex items-center gap-2 py-8 text-sm text-slate-500">
                <Loader2 size={16} className="animate-spin" />
                Cargando cuaderno…
              </div>
            ) : (
              <ul className="mt-4 space-y-3">
                {dayEntries.map((entry) => (
                  <li
                    key={entry.id}
                    className="rounded-xl border border-slate-100 bg-slate-50/80 p-3"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <span
                          className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${CATEGORY_STYLE[entry.category]}`}
                        >
                          {categoryLabel(entry.category)}
                        </span>
                        <h3 className="mt-1 text-sm font-bold text-slate-800">
                          {entry.title}
                        </h3>
                        {entry.body && (
                          <p className="mt-1 whitespace-pre-wrap text-sm text-slate-600">
                            {entry.body}
                          </p>
                        )}
                        <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-slate-400">
                          {entry.reminder_at && (
                            <span className="inline-flex items-center gap-1">
                              <Clock size={11} />
                              {reminderTime(entry.reminder_at)}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex shrink-0 gap-1">
                        <button
                          type="button"
                          onClick={() => fillForm(entry)}
                          className="rounded-lg p-1.5 text-slate-500 hover:bg-white"
                          aria-label="Editar anotación"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleDelete(entry.id)}
                          className="rounded-lg p-1.5 text-slate-400 hover:bg-white hover:text-red-600"
                          aria-label="Borrar anotación"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <form
            onSubmit={(e) => void handleSubmit(e)}
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-800">
              {editingId ? <Pencil size={15} /> : <Plus size={15} />}
              {editingId ? "Editar anotación" : "Nueva anotación"}
            </h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="sm:col-span-2 text-xs font-semibold text-slate-600">
                Título
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Ej. Revisar goteros de la ladera"
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 outline-none focus:border-blue-400 focus:bg-white"
                />
              </label>
              <label className="text-xs font-semibold text-slate-600">
                Tipo
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value as NotebookCategory)}
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 outline-none focus:border-blue-400 focus:bg-white"
                >
                  {NOTEBOOK_CATEGORIES.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="sm:col-span-2 text-xs font-semibold text-slate-600">
                Anotación
                <textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  rows={4}
                  placeholder="Qué viste, qué hiciste y qué queda pendiente…"
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 outline-none focus:border-blue-400 focus:bg-white"
                />
              </label>
              <label className="text-xs font-semibold text-slate-600">
                Recordatorio (hora)
                <input
                  type="time"
                  value={reminder}
                  onChange={(e) => setReminder(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 outline-none focus:border-blue-400 focus:bg-white"
                />
              </label>
            </div>
            {error && <p className="mt-3 text-xs font-semibold text-red-600">{error}</p>}
            <div className="mt-4 flex gap-2">
              <button
                type="submit"
                disabled={saving}
                className="inline-flex items-center gap-2 rounded-xl bg-[#0038A8] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
              >
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                {editingId ? "Guardar cambios" : "Guardar anotación"}
              </button>
              {editingId && (
                <button
                  type="button"
                  onClick={resetForm}
                  className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600"
                >
                  Cancelar
                </button>
              )}
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}
