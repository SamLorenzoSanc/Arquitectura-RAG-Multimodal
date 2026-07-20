import { useEffect, useState } from 'react';
import api from "@/api";

interface Documento {
  id: string;
  content: string;
  metadata: Record<string, any>;
}

const ChromaDebugPage = () => {
  const [data, setData] = useState<{ total_en_documents: number; documentos: Documento[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const response = await api.get('/chat/list-all-documents');
        setData(response.data);
      } catch (err) {
        setError('Error al conectar con la base de datos de Chroma');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchDocs();
  }, []);

  if (loading) return <div className="p-8 text-center">Cargando inspección de base de datos...</div>;
  if (error) return <div className="p-8 text-red-500 font-bold">{error}</div>;

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <h1 className="text-3xl font-extrabold text-gray-900 mb-6">Inspección de ChromaDB</h1>
      
      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-8">
        <p className="text-blue-700 font-semibold text-lg">
          Total de documentos indexados: {data?.total_en_documents || 0}
        </p>
      </div>

      <div className="bg-white shadow-xl rounded-lg overflow-hidden border border-gray-200">
        <table className="w-full text-sm text-left">
          <thead className="bg-gray-100 uppercase text-gray-600 font-bold">
            <tr>
              <th className="px-6 py-4">ID</th>
              <th className="px-6 py-4">Tenant ID</th>
              <th className="px-6 py-4">Contenido (Preview)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {data?.documentos?.length ? (
              data.documentos.map((doc) => (
                <tr key={doc.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 font-mono text-xs text-gray-500">{doc.id}</td>
                  <td className="px-6 py-4 font-semibold text-blue-600">
                    {doc.metadata?.tenant_id || <span className="text-gray-400 font-normal">N/A</span>}
                  </td>
                  <td className="px-6 py-4 text-gray-700 max-w-md truncate">
                    {doc.content ? doc.content.substring(0, 120) : 'Sin contenido'}...
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={3} className="px-6 py-10 text-center text-gray-500">
                  No se encontraron documentos en la colección.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ChromaDebugPage;