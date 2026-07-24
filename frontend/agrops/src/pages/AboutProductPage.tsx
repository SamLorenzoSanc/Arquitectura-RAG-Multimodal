import { ThermometerSnowflake, ShieldCheck, MessageSquare, Bot, ArrowRight, CheckCircle2, Building2, Truck } from "lucide-react";
import { Link } from "react-router-dom";

export default function AboutProductPage() {
    return (
        <div className="min-h-screen bg-slate-50 font-sans selection:bg-emerald-200 selection:text-emerald-900">
            {/* Cabecera / Navegación Superior */}
            <header className="h-20 bg-white/90 backdrop-blur-md border-b border-slate-200 flex justify-between items-center px-8 sticky top-0 z-50 shadow-sm">
                <Link to="/" className="flex items-center gap-2.5 group">
                    <div className="h-10 w-10 rounded-2xl bg-emerald-600 flex items-center justify-center text-white shadow-md shadow-emerald-600/30">
                        <ThermometerSnowflake size={22} />
                    </div>
                    <div>
                        <span className="text-base font-black tracking-tight text-slate-900 block leading-tight">CanariasCold</span>
                        <span className="text-[10px] font-mono text-emerald-600 font-bold block leading-none mt-0.5">Trazabilidad Multimodal</span>
                    </div>
                </Link>
                <div className="flex items-center gap-3">
                    <Link to="/login" className="text-xs font-bold text-slate-700 hover:text-slate-900 px-4 py-2.5 transition">
                        Iniciar Sesión
                    </Link>
                    <Link to="/register" className="bg-emerald-600 hover:bg-emerald-700 text-white px-4.5 py-2.5 rounded-xl text-xs font-bold shadow-md shadow-emerald-600/20 transition flex items-center gap-1.5">
                        Registrar Explotación <ArrowRight size={14} />
                    </Link>
                </div>
            </header>

            {/* Contenido Principal */}
            <main className="mx-auto max-w-5xl px-6 py-16 space-y-16">
                <div className="text-center space-y-4">
                    <span className="inline-block bg-emerald-100 text-emerald-800 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
                        Innovación Agro-Logística
                    </span>
                    <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
                        Acerca de CanariasCold & AgroPS
                    </h1>
                    <p className="max-w-2xl mx-auto text-base text-slate-600">
                        La plataforma definitiva diseñada para garantizar la cadena de frío, mitigar riesgos de mermas y aportar total tranquilidad a agricultores y cooperativas en sus exportaciones hacia la Península.
                    </p>
                </div>

                {/* Bloques de Características */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="p-8 rounded-3xl bg-white border border-slate-200 shadow-sm space-y-4">
                        <div className="p-3 bg-emerald-50 text-emerald-600 rounded-2xl w-fit">
                            <ThermometerSnowflake size={24} />
                        </div>
                        <h3 className="text-lg font-bold text-slate-900">Trazabilidad Multimodal de Extremo a Extremo</h3>
                        <p className="text-sm text-slate-600 leading-relaxed">
                            Controlamos cada etapa del trayecto: desde la cosecha en la finca del agricultor, el paso por el centro de acopio cooperativo, el tránsito marítimo en buques comerciales y la última milla terrestre en tráileres refrigerados hasta Mercamadrid.
                        </p>
                    </div>

                    <div className="p-8 rounded-3xl bg-white border border-slate-200 shadow-sm space-y-4">
                        <div className="p-3 bg-blue-50 text-blue-600 rounded-2xl w-fit">
                            <MessageSquare size={24} />
                        </div>
                        <h3 className="text-lg font-bold text-slate-900">Sistema de Alertas por WhatsApp Business API</h3>
                        <p className="text-sm text-slate-600 leading-relaxed">
                            Olvídate de la incertidumbre. El sistema vigila la telemetría IoT 24/7 y envía notificaciones inmediatas y automáticas al WhatsApp del productor ante cualquier fluctuación térmica crítica.
                        </p>
                    </div>

                    <div className="p-8 rounded-3xl bg-white border border-slate-200 shadow-sm space-y-4">
                        <div className="p-3 bg-amber-50 text-amber-600 rounded-2xl w-fit">
                            <Building2 size={24} />
                        </div>
                        <h3 className="text-lg font-bold text-slate-900">Gestión para Cooperativas y Productores</h3>
                        <p className="text-sm text-slate-600 leading-relaxed">
                            Cada agricultor tiene acceso a un portal exclusivo donde puede visualizar únicamente sus propios lotes, verificar matrículas de transporte, asignar cámaras *reefer* y consultar históricos gráficos.
                        </p>
                    </div>

                    <div className="p-8 rounded-3xl bg-white border border-slate-200 shadow-sm space-y-4">
                        <div className="p-3 bg-green-50 text-green-600 rounded-2xl w-fit">
                            <Bot size={24} />
                        </div>
                        <h3 className="text-lg font-bold text-slate-900">Asistencia Documental e Inteligencia RAG</h3>
                        <p className="text-sm text-slate-600 leading-relaxed">
                            Indexación inteligente de normativas fitosanitarias, ayudas PAC y proyecciones de mercado basadas en modelos de predicción climática y económica (Prophet / ARIMAX).
                        </p>
                    </div>
                </div>

                {/* Call to Action inferior */}
                <div className="p-10 rounded-3xl bg-slate-900 text-white text-center space-y-6">
                    <h2 className="text-2xl font-bold tracking-tight">¿Listo para asegurar tus cosechas?</h2>
                    <p className="text-sm text-slate-300 max-w-xl mx-auto">
                        Únete a los agricultores que ya gestionan sus envíos con total transparencia y seguridad en la cadena de custodia.
                    </p>
                    <Link to="/register" className="inline-flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-slate-900 font-bold px-6 py-3 rounded-xl text-xs transition shadow-lg">
                        Registrar mi Explotación <ArrowRight size={16} />
                    </Link>
                </div>
            </main>
        </div>
    );
}