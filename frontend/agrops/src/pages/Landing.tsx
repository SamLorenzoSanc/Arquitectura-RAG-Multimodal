import {ArrowRight,Bot,Database,FileText, Sparkles} from "lucide-react";
import { Link } from "react-router-dom";

export default function Landing() {
    return (
        <div className="min-h-screen bg-slate-50">

            <section className="mx-auto flex max-w-7xl flex-col items-center px-6 py-24 text-center">

                <span className="rounded-full bg-green-100 px-4 py-2 text-sm font-semibold text-green-700">
                    Portal de Documentacion AgroTech
                </span>

                <h1 className="mt-8 max-w-4xl text-6xl font-extrabold text-slate-900">

                    Tu asistente inteligente para gestionar toda tu documentación agrícola

                </h1>

                <p className="mt-6 max-w-3xl text-xl leading-8 text-slate-600">

                    Consulta subvenciones, normativa, ayudas PAC y cualquier documento
                    utilizando lenguaje natural gracias a un sistema RAG impulsado por IA.

                </p>

                <div className="mt-12 flex gap-6">

                    <Link
                        to="/login"
                        className="rounded-xl bg-green-600 px-8 py-4 font-semibold text-white transition hover:bg-green-700"
                    >
                        Comenzar
                    </Link>

                    <Link
                        to="/register"
                        className="flex items-center gap-2 rounded-xl border border-slate-300 px-8 py-4 font-semibold hover:bg-slate-100"
                    >
                        Crear cuenta
                        <ArrowRight size={18}/>
                    </Link>

                </div>

            </section>

            {/* FEATURES */}

            <section className="mx-auto grid max-w-6xl gap-8 px-6 pb-20 md:grid-cols-2 lg:grid-cols-4">

                <FeatureCard
                    icon={<Bot size={42}/>}
                    title="Asistente IA"
                    text="Responde preguntas utilizando tus documentos."
                />

                <FeatureCard
                    icon={<Database size={42}/>}
                    title="Bases de conocimiento"
                    text="Gestiona múltiples colecciones documentales."
                />

                <FeatureCard
                    icon={<FileText size={42}/>}
                    title="Documentación"
                    text="Sube PDFs y deja que la IA los indexe automáticamente."
                />

                <FeatureCard
                    icon={<Sparkles size={42}/>}
                    title="Búsqueda inteligente"
                    text="Obtén respuestas precisas en segundos."
                />

            </section>

            <section className="bg-white py-20">

                <div className="mx-auto max-w-6xl px-6">

                    <h2 className="text-center text-4xl font-bold">

                        ¿Cómo funciona?

                    </h2>

                    <div className="mt-16 grid gap-12 md:grid-cols-3">

                        <Step
                            number="1"
                            title="Sube tus documentos"
                            text="Añade normativa, subvenciones o cualquier documentación agrícola."
                        />

                        <Step
                            number="2"
                            title="Procesamiento RAG"
                            text="El sistema genera automáticamente embeddings e indexa el contenido."
                        />

                        <Step
                            number="3"
                            title="Pregunta en lenguaje natural"
                            text="Obtén respuestas fundamentadas en tus documentos."
                        />

                    </div>

                </div>

            </section>

            {/* CTA */}

            <section className="bg-green-700 py-20">

                <div className="mx-auto max-w-5xl text-center">

                    <h2 className="text-5xl font-bold text-white">

                        Empieza a trabajar con AgroPS

                    </h2>

                    <p className="mt-6 text-xl text-green-100">

                        Centraliza toda tu documentación y deja que la inteligencia
                        artificial haga el resto.

                    </p>

                    <Link
                        to="/register"
                        className="mt-10 inline-flex rounded-xl bg-white px-10 py-4 font-bold text-green-700"
                    >
                        Crear cuenta
                    </Link>

                </div>

            </section>

        </div>
    );
}

function FeatureCard({
    icon,
    title,
    text,
}:{
    icon: React.ReactNode;
    title:string;
    text:string;
}){

    return(

        <div className="rounded-2xl bg-white p-8 shadow transition hover:-translate-y-1 hover:shadow-xl">

            <div className="text-green-600">

                {icon}

            </div>

            <h3 className="mt-6 text-xl font-bold">

                {title}

            </h3>

            <p className="mt-4 text-slate-600">

                {text}

            </p>

        </div>

    )

}

function Step({
    number,
    title,
    text
}:{
    number:string;
    title:string;
    text:string;
}){

    return(

        <div className="text-center">

            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-600 text-2xl font-bold text-white">

                {number}

            </div>

            <h3 className="mt-6 text-2xl font-bold">

                {title}

            </h3>

            <p className="mt-4 text-slate-600">

                {text}

            </p>

        </div>

    )

}