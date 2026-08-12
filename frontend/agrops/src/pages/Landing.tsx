import { 
    ArrowRight, 
    Bot, 
    TrendingUp, 
    ShieldCheck, 
    Building2, 
    Sparkles, 
    ChevronRight, 
    ThermometerSnowflake, 
    MessageSquare, 
    Info, 
    Leaf 
} from "lucide-react";
import { Link } from "react-router-dom";

export default function Landing() {
    return (
        <div className="min-h-screen bg-slate-50 font-sans selection:bg-yellow-200 selection:text-blue-900">
            {/* HEADER CORPORATIVO */}
            <header className="h-20 bg-white/95 backdrop-blur-md border-b border-slate-200 flex justify-between items-center px-8 sticky top-0 z-50 shadow-xs">
                <Link to="/" className="flex items-center gap-2.5 group">
                    {/* Icono Bandera de Canarias */}
                    <div className="relative h-10 w-10 flex overflow-hidden rounded-xl shadow-md border border-slate-200 shrink-0 transition-transform group-hover:scale-105">
                        {/* Franjas verticales: Blanco, Azul, Amarillo */}
                        <div className="flex-1 bg-white"></div>
                        <div className="flex-1 bg-[#15539C]"></div>
                        <div className="flex-1 bg-[#FFD300]"></div>
                        
                        {/* Termómetro superpuesto con efecto cristal */}
                        <div className="absolute inset-0 flex items-center justify-center">
                            <div className="bg-slate-900/70 backdrop-blur-[2px] p-1 rounded-lg text-white shadow-sm">
                                <ThermometerSnowflake size={16} />
                            </div>
                        </div>
                    </div>
                    
                    {/* Texto del Logo */}
                    <span className="text-xl font-black tracking-wider text-slate-900">
                        AGRO<span className="text-[#15539C]">PS</span>
                    </span>
                </Link>

                <nav className="hidden lg:flex items-center gap-8">
                    <Link to="/about" className="text-sm font-semibold text-slate-700 hover:text-blue-600 transition flex items-center gap-1.5">
                        <Info size={16} /> Acerca del Producto
                    </Link>
                    <Link to="/sustainability" className="text-sm font-semibold text-slate-700 hover:text-blue-600 transition flex items-center gap-1.5">
                        <Leaf size={16} /> Sostenibilidad
                    </Link>
                    <Link to="/privacy-policy" className="text-sm font-semibold text-slate-700 hover:text-blue-600 transition flex items-center gap-1.5">
                        <ShieldCheck size={16} /> Política de Privacidad
                    </Link>
                </nav>

                <div className="flex items-center gap-4">
                    <Link to="/login" className="text-sm font-bold text-slate-700 hover:text-blue-700 px-3 py-2 transition">
                        Iniciar Sesión
                    </Link>
                    <Link 
                        to="/register" 
                        className="bg-blue-700 hover:bg-blue-800 text-white px-5 py-2.5 rounded-xl text-sm font-bold shadow-md shadow-blue-700/20 transition flex items-center gap-1.5"
                    >
                        Empieza
                    </Link>
                </div>
            </header>

            {/* HERO SECTION */}
            <section className="relative overflow-hidden bg-gradient-to-b from-blue-50/60 to-slate-50 pt-24 pb-16">
                <div className="mx-auto flex max-w-7xl flex-col items-center px-6 text-center">
                    
                    <span className="flex items-center gap-2 rounded-full border border-yellow-300 bg-yellow-100/50 px-4 py-1.5 text-sm font-semibold text-yellow-800 shadow-sm backdrop-blur-sm">
                        <Sparkles size={16} className="text-yellow-600" />
                        AGROPS & CanariasCold - Innovación Agrícola y Logística
                    </span>

                    <h1 className="mt-8 max-w-4xl text-5xl font-extrabold tracking-tight text-slate-900 sm:text-6xl lg:text-7xl">
                        Tu ecosistema inteligente para la{' '}
                        <span className="bg-gradient-to-r from-blue-600 to-yellow-500 bg-clip-text text-transparent">
                            gestión agrícola y cadena de frío
                        </span>
                    </h1>

                    <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600 sm:text-xl">
                        Centraliza documentos con IA, predice mercados con ARIMAX y garantiza la trazabilidad en tiempo real desde Canarias hasta Mercamadrid.
                    </p>

                    <div className="mt-10 flex flex-col gap-4 sm:flex-row sm:gap-6">
                        <Link
                            to="/login"
                            className="group flex items-center justify-center gap-2 rounded-xl bg-blue-700 px-8 py-4 text-base font-semibold text-white shadow-lg shadow-blue-700/20 transition-all hover:-translate-y-0.5 hover:bg-blue-800 hover:shadow-blue-700/30 active:translate-y-0"
                        >
                            Comenzar ahora
                            <ChevronRight size={20} className="transition-transform group-hover:translate-x-1" />
                        </Link>

                        <Link
                            to="/register"
                            className="flex items-center justify-center gap-2 rounded-xl border-2 border-slate-200 bg-white px-8 py-4 text-base font-semibold text-slate-700 transition-all hover:border-slate-300 hover:bg-slate-50 active:bg-slate-100"
                        >
                            Crear cuenta
                        </Link>
                    </div>
                </div>
            </section>

            {/* HERO IMAGE */}
            <section className="mx-auto max-w-7xl px-6 pb-20">
                <div className="relative overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl shadow-slate-200/50 group">
                    <img 
                        src="https://images.unsplash.com/photo-1586771107445-d3ca888129ff?q=80&w=2072&auto=format&fit=crop" 
                        alt="Agricultura moderna y tecnología con dron y tractor" 
                        className="w-full h-[400px] object-cover transition-transform duration-700 group-hover:scale-105 sm:h-[500px]"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-900/40 via-transparent to-transparent"></div>
                </div>
            </section>

            {/* SERVICES / FEATURES SECTION */}
            <section className="relative mx-auto max-w-7xl px-6 pb-24">
                <div className="mb-16 text-center">
                    <h2 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
                        Servicios Integrales AgroPS & CanariasCold
                    </h2>
                    <p className="mt-4 text-lg text-slate-600">
                        Todo lo que necesitas para digitalizar el campo y blindar tu exportación a la Península.
                    </p>
                </div>

                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    <FeatureCard
                        icon={<Bot size={28} />}
                        title="Asistente Documental IA"
                        text="Sube y consulta normativas, PAC o subvenciones. El sistema RAG indexa PDFs y responde citando la fuente exacta."
                    />
                    <FeatureCard
                        icon={<ThermometerSnowflake size={28} />}
                        title="Trazabilidad Multimodal y Frío"
                        text="Control total de la cadena de frío (Cámara de aire y contenedores reefer) desde fincas en Canarias hasta Mercamadrid."
                    />
                    <FeatureCard
                        icon={<MessageSquare size={28} />}
                        title="Alertas WhatsApp Business"
                        text="Notificaciones automáticas en tiempo real directo al móvil del agricultor ante cualquier desviación térmica."
                    />
                    <FeatureCard
                        icon={<TrendingUp size={28} />}
                        title="Analítica Predictiva"
                        text="Proyecta demanda y precios de cultivos (Plátano, Aguacate, etc.) usando modelos Prophet y ARIMAX conectados al clima."
                    />
                    <FeatureCard
                        icon={<ShieldCheck size={28} />}
                        title="Auditoría RAG Continua"
                        text="Panel de calidad en tiempo real que evalúa exhaustividad (nDCG, MRR) para asegurar que la IA responde sin alucinaciones."
                    />
                    <FeatureCard
                        icon={<Building2 size={28} />}
                        title="Gestión Multi-Tenant"
                        text="Control total de tu workspace. Administra organizaciones, departamentos y asigna roles específicos a tu equipo."
                    />
                </div>
            </section>

            {/* HOW IT WORKS SECTION */}
            <section className="bg-white py-24 sm:py-32 border-t border-slate-100">
                <div className="mx-auto max-w-7xl px-6 lg:px-8">
                    <div className="mx-auto max-w-2xl text-center mb-20">
                        <h2 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
                            ¿Cómo funciona AgroPS?
                        </h2>
                        <p className="mt-4 text-lg leading-8 text-slate-600">
                            Un flujo de trabajo diseñado para que ahorres horas de gestión diaria y asegures tus envíos.
                        </p>
                    </div>

                    <div className="grid gap-12 md:grid-cols-3 md:gap-8">
                        <Step
                            number="1"
                            title="Configura tu Organización"
                            text="Crea tu espacio, vincula tu cuenta de WhatsApp y registra tus fincas, cooperativas y rutas."
                            imgSrc="https://images.unsplash.com/photo-1605000797499-95a51c5269ae?q=80&w=800&auto=format&fit=crop"
                            alt="Agricultor usando una tablet en el campo"
                        />
                        <Step
                            number="2"
                            title="Alimenta el Sistema"
                            text="Sube documentos normativos a ChromaDB y activa la supervisión IoT de contenedores reefer."
                            imgSrc="https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?q=80&w=800&auto=format&fit=crop"
                            alt="Gestión de documentos y análisis de datos en ordenador portátil"
                        />
                        <Step
                            number="3"
                            title="Monitorea y Tranquilidad"
                            text="Consulta proyecciones de mercado y recibe alertas instantáneas en tu móvil si la cadena de frío sufre variaciones."
                            imgSrc="https://images.unsplash.com/photo-1460925895917-afdab827c52f?q=80&w=800&auto=format&fit=crop"
                            alt="Gráficos de analítica predictiva en pantalla"
                        />
                    </div>
                </div>
            </section>

            {/* SECCIÓN CTA FINAL */}
            <section className="relative overflow-hidden bg-slate-900 py-24 sm:py-32">
                <div className="absolute -left-20 -top-20 h-[400px] w-[400px] rounded-full bg-blue-600/30 blur-[100px]" />
                <div className="absolute -right-20 -bottom-20 h-[400px] w-[400px] rounded-full bg-yellow-400/20 blur-[100px]" />

                <div className="relative mx-auto max-w-5xl px-6 text-center">
                    <h2 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
                        Centraliza hoy tu gestión agrícola y logística
                    </h2>
                    <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-300">
                        Deja que la inteligencia artificial y el monitoreo de temperatura en tiempo real se encarguen de lo complejo para que tú puedas centrarte en el campo.
                    </p>
                    
                    <div className="mt-10 flex items-center justify-center gap-x-6">
                        <Link
                            to="/register"
                            className="group flex items-center gap-2 rounded-xl bg-yellow-400 px-8 py-4 text-base font-semibold text-blue-900 transition-all hover:bg-yellow-500 hover:shadow-lg hover:shadow-yellow-500/20"
                        >
                            Crear mi cuenta gratuita
                            <ArrowRight size={18} className="transition-transform group-hover:translate-x-1" />
                        </Link>
                    </div>
                </div>
            </section>
        </div>
    );
}

// COMPONENTES AUXILIARES ACTUALIZADOS CON LA PALETA AZUL/AMARILLA

function FeatureCard({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
    return (
        <div className="group flex flex-col rounded-2xl border border-slate-200 bg-white p-8 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-blue-200 hover:shadow-xl hover:shadow-blue-900/5 hover:ring-1 hover:ring-blue-200">
            <div className="mb-6 inline-flex h-14 w-14 items-center justify-center rounded-xl bg-blue-50 text-blue-700 transition-colors group-hover:bg-blue-100 group-hover:text-blue-800">
                {icon}
            </div>
            <h3 className="mb-3 text-xl font-bold text-slate-900">
                {title}
            </h3>
            <p className="text-base leading-relaxed text-slate-600 flex-grow">
                {text}
            </p>
        </div>
    );
}

function Step({ number, title, text, imgSrc, alt }: { number: string; title: string; text: string; imgSrc: string; alt: string }) {
    return (
        <div className="relative flex flex-col items-center text-center group">
            <div className="relative w-full mb-8 overflow-hidden rounded-2xl bg-slate-100 shadow-md">
                <img 
                    src={imgSrc} 
                    alt={alt} 
                    className="h-48 w-full object-cover transition-transform duration-500 group-hover:scale-110"
                />
                <div className="absolute inset-0 bg-slate-900/10 group-hover:bg-transparent transition-colors"></div>
                
                <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 flex h-12 w-12 items-center justify-center rounded-full bg-blue-700 text-xl font-bold text-white shadow-lg ring-4 ring-white">
                    {number}
                </div>
            </div>
            
            <h3 className="mt-4 text-xl font-bold text-slate-900">
                {title}
            </h3>
            <p className="mt-3 text-base leading-relaxed text-slate-600 px-4">
                {text}
            </p>
        </div>
    );
}