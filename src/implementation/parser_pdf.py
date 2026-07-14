import pathlib
import pymupdf4llm


def convert_pdf_to_markdown(pdf_path: str, out_dir: str) -> pathlib.Path:
    pdf_path_lib = pathlib.Path(pdf_path)
    md = pymupdf4llm.to_markdown(pdf_path_lib)

    out_dir_lib = pathlib.Path(out_dir)
    out_dir_lib.mkdir(parents=True, exist_ok=True)

    out: pathlib.Path = out_dir_lib / f"{pdf_path_lib.stem}.md"

    out.write_text(md, encoding="utf-8")

    print(f"Saved markdown to {out.resolve()}")

    return out


if __name__ == "__main__":
    BASE_DIR = pathlib.Path(__file__).resolve().parent
    
    assets_dir = BASE_DIR / "assets"
    out_dir = BASE_DIR / "out"

    assets_dir.mkdir(parents=True, exist_ok=True)

    pdfs = list(assets_dir.glob("*.pdf"))
    print(f"Archivos PDF encontrados en {assets_dir}: {len(pdfs)}")

    for pdf in pdfs:
        print(f"Procesando: {pdf.name}")
        convert_pdf_to_markdown(str(pdf), str(out_dir))
