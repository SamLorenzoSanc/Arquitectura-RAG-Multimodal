import sys
from pathlib import Path

from faster_whisper import WhisperModel

print("=" * 70)
print("TEST REAL FASTER-WHISPER + CUDA")
print("=" * 70)

print("\n[1] Python")
print(sys.version)
print(sys.executable)

print("\n[2] Cargando modelo")

model = WhisperModel(
    "large-v3",
    device="cuda",
    compute_type="float16",
)

print("Modelo cargado correctamente")

# Cambia esta ruta por un audio pequeño
audio_path = Path("test_audio.mp4")

if not audio_path.exists():
    print()
    print(f"ERROR: No existe {audio_path}")
    print("Pon un archivo test_audio.mp3 junto a este script.")
    sys.exit(1)

print("\n[3] Iniciando transcripción REAL")
print(f"Archivo: {audio_path}")

try:
    segments, info = model.transcribe(
        str(audio_path),
        beam_size=5,
    )

    print("\n[4] Transcripción iniciada correctamente")
    print(f"Idioma: {info.language}")
    print(f"Probabilidad idioma: {info.language_probability}")

    print("\n[5] Segmentos")

    count = 0

    for segment in segments:
        count += 1

        print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] " f"{segment.text}")

    print()
    print(f"Segmentos generados: {count}")

except Exception as exc:
    print()
    print("=" * 70)
    print("ERROR DURANTE LA TRANSCRIPCIÓN")
    print("=" * 70)
    print(f"Tipo: {type(exc).__name__}")
    print(f"Error: {exc}")

    import traceback

    traceback.print_exc()

    sys.exit(1)

print()
print("=" * 70)
print("RESULTADO")
print("=" * 70)
print("CUDA + CTranslate2 + Faster-Whisper + TRANSCRIPCIÓN: OK")
