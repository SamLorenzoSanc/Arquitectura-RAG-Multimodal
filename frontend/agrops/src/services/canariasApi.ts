// Servicio para consumir la API de Datos Abiertos de Canarias (CKAN API)
const BASE_URL = "https://datos.canarias.es/catalogos/general/api/action";

export interface DatasetCanarias {
    id: string;
    title: string;
    notes: string;
    organization: {
        title: string;
    };
    resources: Array<{
        format: string;
        url: string;
    }>;
}

export async function buscarCultivosYFincasOpenData(): Promise<DatasetCanarias[]> {
    try {

        const response = await fetch(`${BASE_URL}/package_search?q=agricultura+cultivos+fincas&rows=10`, {
            method: "GET",
            headers: {
                "Accept": "application/json"
            }
        });

        if (!response.ok) {
            throw new Error(`Error en la petición a la API: ${response.statusText}`);
        }

        const data = await response.json();
        
        if (data.success && data.result && data.result.results) {
            return data.result.results;
        }

        return [];
    } catch (error) {
        console.error("Error al conectar con la API de Datos Abiertos de Canarias:", error);
        throw error;
    }
}