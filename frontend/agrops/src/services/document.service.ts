import api from "@/api";

export async function listDocuments() {

    const response = await api.get("/documents");

    return response.data;
}

export async function uploadDocument(file: File) {

    const form = new FormData();

    form.append("file", file);

    const response = await api.post(
        "/documents/upload",
        form,
        {
            headers: {
                "Content-Type": "multipart/form-data",
            },
        }
    );

    return response.data;
}