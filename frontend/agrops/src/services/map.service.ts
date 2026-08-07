import api from "@/api";

class MapService {

    async getCultivos() {

        const response = await fetch(
            `${api}/map/crops`
        );

        if (!response.ok)
            throw new Error("Error");
        return response.json();
    }
}

export default new MapService();