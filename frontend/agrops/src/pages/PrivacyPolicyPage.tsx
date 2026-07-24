import { ShieldCheck, ThermometerSnowflake, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

export default function PrivacyPolicyPage() {
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

            {/* Contenido Legal */}
            <main className="mx-auto max-w-4xl px-6 py-16 space-y-12 bg-white rounded-3xl border border-slate-200 shadow-sm my-12">
                <div className="flex items-center gap-3 border-b border-slate-100 pb-6">
                    <div className="p-3 bg-emerald-50 text-emerald-600 rounded-2xl">
                        <ShieldCheck size={28} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">Política de Privacidad y Términos de Uso</h1>
                        <p className="text-xs text-slate-500 mt-0.5">Última actualización: Julio de 2026 | Cumplimiento RGPD</p>
                    </div>
                </div>

                <div className="space-y-8 text-sm text-slate-600 leading-relaxed">
                    <section className="space-y-3">
                        <h2 className="text-base font-bold text-slate-900">1. Objeto y Ámbito de Aplicación</h2>
                        <p>
                            Las presentes Condiciones de Uso regulan el acceso y la utilización de la plataforma de control logístico y trazabilidad multiruta (Canarias ➔ Mercamadrid), ofrecida a agricultores, cooperativas y operadores de transporte. El registro o uso de la plataforma implica la aceptación expresa de estos términos.
                        </p>
                    </section>

                    <section className="space-y-3">
                        <h2 className="text-base font-bold text-slate-900">2. Servicios de Trazabilidad y Alertas por WhatsApp</h2>
                        <p>
                            La plataforma recopila y muestra datos en tiempo real de temperatura, humedad y ubicación de contenedores <em>reefer</em>. Los usuarios registrados podrán recibir avisos preventivos e incidencias térmicas a través de canales integrados como <strong>WhatsApp Business API</strong> y correo electrónico. El usuario garantiza que el número de teléfono aportado es veraz y de su titularidad exclusiva.
                        </p>
                    </section>

                    <section className="space-y-3">
                        <h2 className="text-base font-bold text-slate-900">3. Responsable del Tratamiento y Datos Recopilados</h2>
                        <p>
                            El responsable del tratamiento de los datos es la organización gestora de la plataforma. Para garantizar la trazabilidad logística y el servicio de alertas, recopilamos:
                        </p>
                        <ul className="list-disc list-inside space-y-1 pl-2">
                            <li>Datos identificativos y de contacto (Nombre, correo electrónico y número de teléfono móvil para WhatsApp Business).</li>
                            <li>Datos profesionales y de explotación (Ubicación de fincas, cooperativas de origen, matrículas de transporte y lotes agrícolas).</li>
                            <li>Datos de telemetría asociados a los contenedores de transporte.</li>
                        </ul>
                    </section>

                    <section className="space-y-3">
                        <h2 className="text-base font-bold text-slate-900">4. Legitimación y Destinatarios</h2>
                        <p>
                            El tratamiento de los datos se fundamenta en la ejecución del contrato de servicios logísticos y en el consentimiento explícito del agricultor al vincular su cuenta de WhatsApp. Para el envío de mensajes automatizados se utiliza la infraestructura de <strong>Meta Platforms, Inc.</strong> bajo estrictos estándares de confidencialidad.
                        </p>
                    </section>

                    <section className="space-y-3">
                        <h2 className="text-base font-bold text-slate-900">5. Derechos de los Usuarios</h2>
                        <p>
                            El usuario puede ejercer en cualquier momento sus derechos de acceso, rectificación, supresión y portabilidad, así como revocar el consentimiento de notificaciones por WhatsApp de forma inmediata desde su panel de configuración o contactando con el soporte técnico de la empresa.
                        </p>
                    </section>
                </div>
            </main>
        </div>
    );
}