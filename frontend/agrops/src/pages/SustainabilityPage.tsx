import { 
    Leaf, 
    TrendingDown, 
    Droplets, 
    ShieldCheck, 
    Sparkles, 
    ArrowRight, 
    Download, 
    BarChart3, 
    Cpu, 
    Users, 
    CheckCircle2, 
    ThermometerSnowflake 
} from "lucide-react";
import { Link } from "react-router-dom";

export default function SustainabilityPage() {
    return (
        <div className="min-h-screen bg-slate-50 font-sans selection:bg-emerald-200 selection:text-emerald-900">
            {/* HEADER CORPORATIVO */}
            <header className="h-20 bg-white/95 backdrop-blur-md border-b border-slate-200 flex justify-between items-center px-8 sticky top-0 z-50 shadow-xs">
                <Link to="/" className="flex items-center gap-2 group">
                    <div className="h-9 w-9 rounded-xl bg-emerald-700 flex items-center justify-center text-white shadow-md shadow-emerald-700/20">
                        <ThermometerSnowflake size={20} />
                    </div>
                    <span className="text-xl font-black tracking-wider text-slate-900">
                        AGRO<span className="text-emerald-600">PS</span>
                    </span>
                </Link>

                <nav className="hidden lg:flex items-center gap-8">
                    <Link to="/about" className="text-sm font-semibold text-slate-700 hover:text-emerald-600 transition">
                        Acerca del Producto
                    </Link>
                    <Link to="/sustainability" className="text-sm font-semibold text-emerald-600 transition">
                        Sostenibilidad
                    </Link>
                    <Link to="/privacy-policy" className="text-sm font-semibold text-slate-700 hover:text-emerald-600 transition">
                        Política de Privacidad
                    </Link>
                </nav>

                <div className="flex items-center gap-4">
                    <Link to="/login" className="text-sm font-bold text-slate-700 hover:text-slate-900 px-3 py-2 transition">
                        Iniciar Sesión
                    </Link>
                    <Link 
                        to="/register" 
                        className="bg-emerald-700 hover:bg-emerald-800 text-white px-5 py-2.5 rounded-xl text-sm font-bold shadow-md shadow-emerald-700/20 transition flex items-center gap-1.5"
                    >
                        Empieza
                    </Link>
                </div>
            </header>

            {/* HERO SECTION CON IMAGEN DE FONDO (CANARIAS) */}
            <section className="relative overflow-hidden pt-32 pb-24 text-white">
                <div className="absolute inset-0 z-0">
                    <img 
                        src="https://images.unsplash.com/photo-1500937386664-56d1dfef3854?q=80&w=2070&auto=format&fit=crop" 
                        alt="Paisaje agrícola de Canarias" 
                        className="w-full h-full object-cover object-center"
                    />
                    <div className="absolute inset-0 bg-slate-950/65 backdrop-blur-[2px]" />
                </div>

                <div className="relative z-10 mx-auto flex max-w-5xl flex-col items-center px-6 text-center">
                    <span className="flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-900/60 px-4 py-1.5 text-sm font-semibold text-emerald-200 shadow-sm backdrop-blur-md">
                        <Leaf size={16} className="text-emerald-400" />
                        Agricultura Insular Sostenible y Cadena de Frío
                    </span>

                    <h1 className="mt-6 text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl text-white">
                        Una agricultura de altas cumbres y costa más sostenible para Canarias
                    </h1>

                    <p className="mt-6 max-w-2xl text-lg leading-relaxed text-slate-200">
                        Optimizamos los recursos hídricos insulares, el cultivo de plátanos y aguacates, y blindamos la exportación hacia Mercamadrid reduciendo la huella de carbono.
                    </p>
                </div>
            </section>

            {/* POR QUÉ ES IMPORTANTE */}
            <section className="mx-auto max-w-7xl px-6 py-16">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                    <div className="space-y-6">
                        <div className="inline-flex p-3 bg-emerald-100 text-emerald-700 rounded-2xl">
                            <Sparkles size={24} />
                        </div>
                        <h2 className="text-3xl font-bold tracking-tight text-slate-900">
                            Por qué la sostenibilidad es vital en la agricultura insular
                        </h2>
                        <p className="text-slate-600 text-base leading-relaxed">
                            Las particularidades geográficas y climáticas de Canarias exigen un compromiso absoluto con el medio ambiente:
                        </p>
                        <ul className="space-y-4 text-slate-700 font-medium">
                            <li className="flex items-start gap-3 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
                                <span className="text-emerald-600 font-bold">•</span>
                                <div>
                                    <strong className="text-slate-900">Escasez hídrica y galerías:</strong> El agua es un recurso extremadamente limitado en las islas, requiriendo un control milimétrico del riego por goteo.
                                </div>
                            </li>
                            <li className="flex items-start gap-3 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
                                <span className="text-emerald-600 font-bold">•</span>
                                <div>
                                    <strong className="text-slate-900">Huella de insularidad y transporte:</strong> Exportar al mercado peninsular exige optimizar la logística de contenedores *reefer* para minimizar emisiones.
                                </div>
                            </li>
                            <li className="flex items-start gap-3 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
                                <span className="text-emerald-600 font-bold">•</span>
                                <div>
                                    <strong className="text-slate-900">Vulnerabilidad climática:</strong> El archipiélago sufre de manera directa los efectos del calentamiento global, afectando a microclimas y cultivos tradicionales.
                                </div>
                            </li>
                            <li className="flex items-start gap-3 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
                                <span className="text-emerald-600 font-bold">•</span>
                                <div>
                                    <strong className="text-slate-900">Normativa agraria europea (REOGA/PAC):</strong> Adaptación a los estrictos estándares ecológicos de la Unión Europea en el marco insular.
                                </div>
                            </li>
                        </ul>
                        <p className="text-xs text-slate-400 font-mono">*Fuente: Gobierno de Canarias & IPCC Climate Change Report</p>
                    </div>

                    <div className="space-y-6">
                        <div className="p-8 rounded-3xl bg-emerald-900 text-white shadow-xl space-y-6 relative overflow-hidden">
                            <div className="absolute right-0 top-0 translate-x-8 -translate-y-8 w-48 h-48 bg-emerald-800 rounded-full blur-2xl opacity-50 pointer-events-none" />
                            <h3 className="text-xl font-bold">¿Cómo mejoramos la sostenibilidad en Canarias?</h3>
                            <p className="text-emerald-100 text-sm leading-relaxed">
                                Aplicamos tecnología adaptada al territorio volcánico y agrícola de las islas:
                            </p>
                            <div className="space-y-4">
                                <div className="bg-emerald-800/60 p-4 rounded-2xl border border-emerald-700/50">
                                    <h4 className="font-bold text-sm text-white">1. Eficiencia Hídrica Avanzada</h4>
                                    <p className="text-xs text-emerald-200 mt-1">Sensores IoT en fincas para evitar pérdidas en redes de riego tradicionales.</p>
                                </div>
                                <div className="bg-emerald-800/60 p-4 rounded-2xl border border-emerald-700/50">
                                    <h4 className="font-bold text-sm text-white">2. Cadena de Frío Inteligente</h4>
                                    <p className="text-xs text-emerald-200 mt-1">Cero desperdicio de alimento en tránsito marítimo hacia la Península gracias a alertas automáticas.</p>
                                </div>
                                <div className="bg-emerald-800/60 p-4 rounded-2xl border border-emerald-700/50">
                                    <h4 className="font-bold text-sm text-white">3. Prácticas Regenerativas</h4>
                                    <p className="text-xs text-emerald-200 mt-1">Protección y enriquecimiento de los suelos volcánicos para fomentar la retención orgánica.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* SECCIÓN CON LA NUEVA IMAGEN DE LAS MANOS SOSTENIENDO PLANTA */}
            <section className="bg-emerald-950 text-white py-20 my-8 overflow-hidden">
                <div className="mx-auto max-w-7xl px-6 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                    <div className="relative overflow-hidden rounded-3xl shadow-2xl border border-emerald-800/50 group">
                        <img 
                            src="https://cdn.prod.website-files.com/64634f7e4648fab8dc7f7917/64d24247b8023ce59b5a1ef2_Rectangle%20693.jpg" 
                            alt="Manos sosteniendo tierra fértil con brote verde en Canarias" 
                            className="w-full h-[400px] object-cover transition-transform duration-700 group-hover:scale-105"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-emerald-950/80 via-transparent to-transparent" />
                    </div>

                    <div className="space-y-6">
                        <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 bg-emerald-900/80 px-3 py-1.5 rounded-xl border border-emerald-700">
                            Compromiso con el Suelo Volcánico
                        </span>
                        <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
                            Cuidando el origen de nuestros cultivos insulares
                        </h2>
                        <p className="text-emerald-100 text-base leading-relaxed">
                            La riqueza de los suelos volcánicos de Canarias es única, pero requiere un cuidado riguroso. Al integrar digitalización y control de humedad, protegemos cada hectárea de platanera y frutal, garantizando cosechas sostenibles de kilómetro cero con proyección exterior.
                        </p>
                        <div className="grid grid-cols-2 gap-4 pt-2">
                            <div className="p-4 rounded-2xl bg-emerald-900/60 border border-emerald-800">
                                <p className="text-2xl font-black text-emerald-300 font-mono">100%</p>
                                <p className="text-xs text-emerald-200 mt-1">Control de origen insular</p>
                            </div>
                            <div className="p-4 rounded-2xl bg-emerald-900/60 border border-emerald-800">
                                <p className="text-2xl font-black text-emerald-300 font-mono">24/7</p>
                                <p className="text-xs text-emerald-200 mt-1">Trazabilidad y frío</p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* SOSTENIBILIDAD PARA EL SECTOR AGROALIMENTARIO */}
            <section className="bg-white py-20 border-y border-slate-100">
                <div className="mx-auto max-w-7xl px-6 space-y-16">
                    <div className="text-center space-y-4 max-w-3xl mx-auto">
                        <h2 className="text-3xl font-bold tracking-tight text-slate-900">
                            Sostenibilidad para el sector agroalimentario de exportación
                        </h2>
                        <p className="text-slate-600 text-base">
                            Las cooperativas y empresas exportadoras de Canarias se enfrentan a exigencias globales de sostenibilidad:
                        </p>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                        <div className="relative overflow-hidden rounded-3xl shadow-xl border border-slate-200 bg-slate-100 group">
                            <img 
                                src="https://cdn.prod.website-files.com/64634f7e4648fab8dc7f7917/653fc6cc5b3f926a01e5d8f1_Frame%20221.webp" 
                                alt="Sostenibilidad en el sector agroalimentario" 
                                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                            />
                        </div>

                        <div className="grid grid-cols-1 gap-6">
                            <div className="p-6 rounded-3xl bg-slate-50 border border-slate-200 space-y-3">
                                <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">01</div>
                                <h3 className="font-bold text-slate-900">Exigencia de los Mercados Peninsulares</h3>
                                <p className="text-sm text-slate-600">Los distribuidores en Mercamadrid exigen certificaciones estrictas de origen y bajas emisiones en transporte.</p>
                            </div>
                            <div className="p-6 rounded-3xl bg-slate-50 border border-slate-200 space-y-3">
                                <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">02</div>
                                <h3 className="font-bold text-slate-900">Optimización de Alcance 3</h3>
                                <p className="text-sm text-slate-600">Control riguroso de las emisiones asociadas al transporte marítimo y la cadena de frío interinsular.</p>
                            </div>
                            <div className="p-6 rounded-3xl bg-slate-50 border border-slate-200 space-y-3">
                                <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">03</div>
                                <h3 className="font-bold text-slate-900">Cumplimiento ESG y Metas Verdes</h3>
                                <p className="text-sm text-slate-600">Facilitamos informes auditables para cumplir con los estándares europeos de sostenibilidad corporativa.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* LO QUE HEMOS HECHO HASTA AHORA (MÉTRICAS) */}
            <section className="mx-auto max-w-7xl px-6 py-20">
                <div className="text-center space-y-4 mb-16">
                    <span className="text-xs font-bold uppercase tracking-wider text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
                        Impacto Verificado en el Archipiélago
                    </span>
                    <h2 className="text-3xl font-bold tracking-tight text-slate-900">
                        Lo que hemos logrado hasta ahora
                    </h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
                    <div className="p-8 rounded-3xl bg-white border border-slate-200 shadow-sm text-center space-y-4">
                        <div className="inline-flex p-3 bg-emerald-50 text-emerald-600 rounded-2xl">
                            <TrendingDown size={32} />
                        </div>
                        <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Dióxido de carbono evitado</p>
                        <p className="text-4xl font-black text-slate-900 font-mono">68.639,41</p>
                        <p className="text-xs font-semibold text-emerald-700 bg-emerald-50 py-1.5 px-3 rounded-xl border border-emerald-200 inline-block">
                            tCO2eq — Equivalente al CO2 absorbido por 31.200 árboles en Canarias
                        </p>
                    </div>

                    <div className="p-8 rounded-3xl bg-white border border-slate-200 shadow-sm text-center space-y-4">
                        <div className="inline-flex p-3 bg-blue-50 text-blue-600 rounded-2xl">
                            <Droplets size={32} />
                        </div>
                        <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Agua ahorrada en regadíos</p>
                        <p className="text-4xl font-black text-slate-900 font-mono">3.408.104,95</p>
                        <p className="text-xs font-semibold text-blue-700 bg-blue-50 py-1.5 px-3 rounded-xl border border-blue-200 inline-block">
                            m³ H2O — Optimización vital para los recursos hídricos insulares
                        </p>
                    </div>
                </div>
            </section>

            {/* CÓMO AYUDAMOS A LA AGRICULTURA A SER MÁS SOSTENIBLE */}
            <section className="bg-slate-900 text-white py-24">
                <div className="mx-auto max-w-6xl px-6 space-y-16">
                    <div className="text-center space-y-4">
                        <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
                            Cómo ayudamos a la agricultura de Canarias
                        </h2>
                        <p className="text-slate-400 max-w-2xl mx-auto text-base">
                            Un enfoque basado en datos locales y control de la cadena logística hacia Mercamadrid.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        <div className="bg-slate-800/80 p-8 rounded-3xl border border-slate-700 space-y-4">
                            <div className="p-3 bg-emerald-600/20 text-emerald-400 rounded-2xl w-fit">
                                <BarChart3 size={24} />
                            </div>
                            <h3 className="text-lg font-bold">1. Recogemos datos de finca</h3>
                            <p className="text-sm text-slate-300 leading-relaxed">
                                Los agricultores canarios registran sus labores, riegos y cosechas en la plataforma para unificar toda la trazabilidad insular.
                            </p>
                        </div>

                        <div className="bg-slate-800/80 p-8 rounded-3xl border border-slate-700 space-y-4">
                            <div className="p-3 bg-emerald-600/20 text-emerald-400 rounded-2xl w-fit">
                                <Cpu size={24} />
                            </div>
                            <h3 className="text-lg font-bold">2. Calculamos el impacto</h3>
                            <p className="text-sm text-slate-300 leading-relaxed">
                                Cooperativas y productores obtienen métricas exactas del impacto ambiental de sus cultivos de exportación en categorías clave:
                            </p>
                            <ul className="text-xs font-mono text-emerald-300 space-y-1 pt-1">
                                <li>• Dióxido de carbono - CO2eq</li>
                                <li>• Agua - m³</li>
                                <li>• Acidificación - SO2eq</li>
                                <li>• Eutrofización - PO4eq</li>
                            </ul>
                        </div>

                        <div className="bg-slate-800/80 p-8 rounded-3xl border border-slate-700 space-y-4">
                            <div className="p-3 bg-emerald-600/20 text-emerald-400 rounded-2xl w-fit">
                                <Users size={24} />
                            </div>
                            <h3 className="text-lg font-bold">3. Asesoramos & Alertas WhatsApp</h3>
                            <p className="text-sm text-slate-300 leading-relaxed">
                                IA agronómica para optimizar fertilización y control térmico en contenedores reefer con avisos directos al móvil del productor.
                            </p>
                        </div>
                    </div>

                    {/* SALIR AL CAMPO */}
                    <div className="p-8 rounded-3xl bg-emerald-950 border border-emerald-800/60 flex flex-col md:flex-row items-center justify-between gap-6">
                        <div className="space-y-2">
                            <h3 className="text-xl font-bold text-white">Apoyo técnico en el archipiélago</h3>
                            <p className="text-xs text-emerald-200 max-w-xl leading-relaxed">
                                Contamos con expertos agrónomos que apoyan a las cooperativas canarias en su transformación digital y cumplimiento de normativas de exportación.
                            </p>
                        </div>
                        <Link to="/register" className="bg-emerald-500 hover:bg-emerald-400 text-slate-900 font-bold px-6 py-3 rounded-xl text-xs transition shadow-lg shrink-0">
                            Únete a la transición
                        </Link>
                    </div>

                    {/* TESTIMONIO CLIENTE */}
                    <blockquote className="border-l-4 border-emerald-500 pl-6 py-2 space-y-3 italic text-slate-300">
                        <p className="text-base">
                            "Digitalizar nuestra cadena logística desde las islas hasta Mercamadrid y asegurar la cadena de frío nos ha permitido certificar un producto sostenible y de máxima calidad."
                        </p>
                        <footer className="text-xs font-semibold text-emerald-400 not-italic">
                            Cooperativa Agrícola de Canarias — Dirección de Operaciones
                        </footer>
                    </blockquote>
                </div>
            </section>

            {/* INFORMES DE IMPACTO */}
            <section className="mx-auto max-w-5xl px-6 py-20 text-center space-y-8">
                <div className="space-y-3">
                    <h2 className="text-3xl font-bold tracking-tight text-slate-900">Nuestros informes de impacto insular</h2>
                    <p className="text-slate-600 max-w-xl mx-auto text-sm">
                        Medimos nuestro impacto de forma transparente para certificar la excelencia ecológica de la agricultura canaria en Europa.
                    </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 max-w-2xl mx-auto">
                    <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-sm space-y-4">
                        <h3 className="font-bold text-slate-900">Informe de impacto 2025</h3>
                        <button onClick={() => alert("Descargando Informe de Impacto 2025...")} className="w-full bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold py-2.5 rounded-xl text-xs transition flex items-center justify-center gap-2 cursor-pointer">
                            <Download size={14} /> Descargar el informe
                        </button>
                    </div>
                    <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-sm space-y-4">
                        <h3 className="font-bold text-slate-900">Informe de impacto 2024</h3>
                        <button onClick={() => alert("Descargando Informe de Impacto 2024...")} className="w-full bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold py-2.5 rounded-xl text-xs transition flex items-center justify-center gap-2 cursor-pointer">
                            <Download size={14} /> Descargar el informe
                        </button>
                    </div>
                </div>
            </section>

            {/* CTA FINAL (GRANJAS Y CADENAS) */}
            <section className="bg-emerald-50/50 py-24 border-t border-emerald-100">
                <div className="mx-auto max-w-7xl px-6 grid grid-cols-1 lg:grid-cols-2 gap-8">
                    <div className="p-8 rounded-3xl bg-white border border-slate-200 shadow-sm space-y-6 flex flex-col justify-between">
                        <div className="space-y-4">
                            <span className="text-xs font-bold text-emerald-700 bg-emerald-100 px-3 py-1 rounded-full">Agricultores y Granjas</span>
                            <h3 className="text-2xl font-bold text-slate-900">Simplifique la gestión de su explotación en Canarias</h3>
                            <ul className="space-y-2 text-xs text-slate-600">
                                <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-emerald-600" /> Optimización de riegos y recursos hídricos</li>
                                <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-emerald-600" /> Ahorro de tiempo en cuadernos de campo digitales</li>
                                <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-emerald-600" /> Monitoreo activo de impacto ambiental</li>
                                <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-emerald-600" /> Alertas directas al WhatsApp personal</li>
                            </ul>
                        </div>
                        <Link to="/register" className="w-full bg-emerald-700 hover:bg-emerald-800 text-white font-bold py-3 rounded-xl text-xs transition text-center shadow-md">
                            Emprende tu viaje
                        </Link>
                    </div>

                    <div className="p-8 rounded-3xl bg-white border border-slate-200 shadow-sm space-y-6 flex flex-col justify-between">
                        <div className="space-y-4">
                            <span className="text-xs font-bold text-blue-700 bg-blue-100 px-3 py-1 rounded-full">Cooperativas y Cadenas</span>
                            <h3 className="text-2xl font-bold text-slate-900">Digitalice su cadena de suministro insular</h3>
                            <ul className="space-y-2 text-xs text-slate-600">
                                <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-blue-600" /> Control de temperatura en tránsito hacia Mercamadrid</li>
                                <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-blue-600" /> Medición y certificación de huella ecológica</li>
                                <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-blue-600" /> Cumplimiento de estándares ESG y trazabilidad</li>
                            </ul>
                        </div>
                        <Link to="/register" className="w-full bg-slate-900 hover:bg-slate-800 text-white font-bold py-3 rounded-xl text-xs transition text-center shadow-md">
                            Reserva una demo
                        </Link>
                    </div>
                </div>
            </section>
        </div>
    );
}