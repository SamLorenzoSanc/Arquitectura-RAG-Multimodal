const SECTIONS = [
  {
    id: "inicio",
    title: "Qué es AgroPS",
    body: "AgroPS es el panel para consultar documentación agrícola con un asistente RAG: subes documentos, preguntas en lenguaje cotidiano y mides si las respuestas se sostienen en el corpus. No hace falta saber de inteligencia artificial para usarlo.",
  },
  {
    id: "organizacion",
    title: "Organización y proyectos",
    body: "Arriba a la izquierda eliges la organización (tu cooperativa o empresa). Dentro hay proyectos, que aquí se llaman bases de conocimiento: cada una agrupa los documentos y las respuestas del asistente de ese ámbito.",
  },
  {
    id: "documentos",
    title: "Datasets",
    body: "En Datasets cada departamento tiene su catálogo. Puedes subir documentos, importar logs de inferencias, generar datos sintéticos o cargar un conjunto demo (POSEI, riego, sanidad). Al subir un documento también se indexa para que el asistente pueda citarlo.",
  },
  {
    id: "asistente",
    title: "Cómo preguntar al asistente",
    body: "El chat (botón flotante o pantalla de asistente) responde con lo que hay en tus documentos. Si no encuentra información, debe decirlo. Las respuestas mejoran cuando los documentos están bien subidos y las preguntas de muestra se validan.",
  },
  {
    id: "cuaderno",
    title: "Cuaderno de campo",
    body: "Sirve para anotar riegos, observaciones o incidencias del día. Es un registro auxiliar; no forma parte de la evaluación del RAG ni sustituye al cuaderno oficial si tu explotación tiene uno.",
  },
  {
    id: "evaluacion",
    title: "Evaluación y validación humana",
    body: "El laboratorio de evaluación mide si el asistente acierta. Un experto puede aprobar o corregir preguntas de muestra. Solo las aprobadas entran en el banco de calidad. No es una pantalla de trabajo diario.",
  },
  {
    id: "ajustes",
    title: "Ajustes, tokens y claves",
    body: "En Ajustes cambias tu nombre, ves el uso de la cuenta y generas un token para llamar al backend desde fuera de la web. El token se muestra una sola vez: cópialo y guárdalo. Si se filtra, revócalo y crea otro.",
  },
  {
    id: "soporte",
    title: "Pedir ayuda",
    body: "Soporte envía un mensaje a los administradores de tu organización. Describe qué estabas haciendo, qué esperabas y qué ocurrió. Ellos verán el aviso en la misma pantalla.",
  },
];

export default function HelpDocsPage() {
  return (
    <div className="mx-auto max-w-3xl pb-10">
      <h1 className="text-xl font-bold text-slate-900">Documentación</h1>
      <p className="mt-1 text-sm text-slate-500">
        Guía breve para usar AgroPS sin conocimientos técnicos.
      </p>
      <nav className="mt-5 flex flex-wrap gap-2">
        {SECTIONS.map((section) => (
          <a
            key={section.id}
            href={`#${section.id}`}
            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-medium text-slate-600 hover:border-blue-200 hover:text-blue-700"
          >
            {section.title}
          </a>
        ))}
      </nav>
      <div className="mt-6 space-y-4">
        {SECTIONS.map((section) => (
          <article
            key={section.id}
            id={section.id}
            className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm"
          >
            <h2 className="text-sm font-bold text-slate-800">{section.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              {section.body}
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}
