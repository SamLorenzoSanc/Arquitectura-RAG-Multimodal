# Corpus de asesoría agraria canaria

Textos originales de marco (POSEI, sanidad, GIP, riego, cuaderno) más dossiers de cultivo generados desde el Registro Oficial de Productos Fitosanitarios del MAPA (`knowledge-base/Vademecum/vademecum_canarias.csv`).

## Cómo indexarlo en AgroPS

1. Crea un proyecto / base de conocimiento «Asesor Canarias».
2. Sube primero `01`–`13` (marco).
3. Sube después `cultivos/*.md`.
4. No subas el JSON de 50 MB ni anexos POSEI con beneficiarios.
5. Si indexas el PDF consolidado POSEI o las órdenes del BOC, usa **Reprocesar OCR** si el texto sale ilegible.

## Regenerar dossiers

```bash
python scripts/descargar_vademecum_mapa.py   # viernes, tras las 14:00
python scripts/generar_corpus_asesor.py
```

Las dosis de los dossiers salen del MAPA. Confirma siempre en https://servicio.mapa.gob.es/regfiweb/ antes de aplicar.
