import chromadb
from pathlib import Path

def migrate_db():
    # 1. Definir rutas absolutas para evitar errores de contexto
    # Asumimos que el script está en la raíz o en una carpeta interna
    base_dir = Path(__file__).parent.parent
    old_path = str(base_dir / "notebooks/preprocessed_db")
    new_path = str(base_dir / "storage/chroma") # Ruta corregida a tu proyecto

    print(f"Migrando desde: {old_path}")
    print(f"Hacia: {new_path}")

    # 2. Clientes
    old_client = chromadb.PersistentClient(path=old_path)
    new_client = chromadb.PersistentClient(path=new_path)

    # 3. Colecciones
    # Asegúrate de que el nombre "docs" sea el correcto en la antigua
    old_col = old_client.get_collection("docs") 
    new_col = new_client.get_or_create_collection("documents") # Nombre estandarizado

    # 4. Extraer datos (por lotes si la base es muy grande)
    print("Extrayendo datos...")
    data = old_col.get(include=["documents", "embeddings", "metadatas"])
    
    if not data["ids"]:
        print("La base de datos antigua está vacía.")
        return

    # 5. Limpieza de metadatos
    metadatas = data["metadatas"]
    for meta in metadatas:
        meta["tenant_id"] = "global"
        # Asegurar que no haya valores None que Chroma rechace
        for k, v in meta.items():
            if v is None: meta[k] = ""
        
        meta["source"] = meta.get("source", "preprocessed")

    # 6. Insertar en la nueva
    print(f"Insertando {len(data['ids'])} documentos en la nueva DB...")
    new_col.add(
        ids=data["ids"],
        embeddings=data["embeddings"],
        documents=data["documents"],
        metadatas=metadatas
    )
    print("Migración completada con éxito.")

if __name__ == "__main__":
    migrate_db()