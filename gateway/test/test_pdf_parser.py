import asyncio
from pathlib import Path

from parsers.pdf_parser import PdfParser


async def main():

    parser = PdfParser()

    parsed = await parser.parse(
        Path("./pago.pdf")
    )

    print(parsed.markdown[:500])

    Path("salida.md").write_text(
        parsed.markdown,
        encoding="utf8"
    )


asyncio.run(main())