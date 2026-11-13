# Klipy „Taktowanie pompy ciepła" (5 × iso, 1080×1920, 30 fps)

Seria wyjaśniająca na podstawie artykułu
`https://www.asta-energy.pl/blog/taktowanie-pompy-ciepla/`.
Każdy klip to samodzielna całość (jeden wątek, pełna wiedza po
obejrzeniu). Teksty w klipach są jedynym źródłem informacji —
bez lektora, więc muszą być bezdyskusyjnie jasne.

| # | klip | manifest | MP4 | storyboard | scen / czas |
|---|---|---|---|---|---|
| 01 | Przegląd | `blog-taktowanie-iso-01-przeglad.json` | `01-przeglad.mp4` | `01-przeglad-storyboard.png` | 10 / ~67 s |
| 02 | Cykle | `blog-taktowanie-iso-02-cykle.json` | `02-cykle.mp4` | `02-cykle-storyboard.png` | 7 / ~50 s |
| 03 | Przyczyny | `blog-taktowanie-iso-03-przyczyny.json` | `03-przyczyny.mp4` | `03-przyczyny-storyboard.png` | 8 / ~57 s |
| 04 | Bufor | `blog-taktowanie-iso-04-bufor.json` | `04-bufor.mp4` | `04-bufor-storyboard.png` | 7 / ~50 s |
| 05 | Nie ruszaj | `blog-taktowanie-iso-05-nie-ruszaj.json` | `05-nie-ruszaj.mp4` | `05-nie-ruszaj-storyboard.png` | 7 / ~50 s |

Pliki: manifesty w `brands/asta-energy/projects/`, gotowe klipy
i storyboardy w `renders/asta-energy/blog-taktowanie-iso/`
(scenariusz całości: `scenariusz.md` w tym folderze).

## Jak odtworzyć dowolny klip

```bash
.venv/bin/python -m reels_maker studio-render \
  brands/asta-energy/projects/blog-taktowanie-iso-01-przeglad.json \
  --output renders/asta-energy/blog-taktowanie-iso/ \
  --profile final --jobs 4
.venv/bin/python -m reels_maker storyboard \
  brands/asta-energy/projects/blog-taktowanie-iso-01-przeglad.json \
  --video renders/asta-energy/blog-taktowanie-iso/01-przeglad.mp4 \
  --output renders/asta-energy/blog-taktowanie-iso/01-przeglad-storyboard.png \
  --motion-strip
```

## Reguły tytułów i układu (lekcja z klipu 01)

- Tytuł sceny zawsze mówi, CZEGO dotyczy (np. „Cykle sprężarki",
  nie „Cykle") — zero domysłów.
- Układ tekstu sceny 1 = układ scen późniejszych.
- Zero owalnych teł i „pływających" elementów dekoracyjnych.
- Dynamiczna kamera: 7 stref push/pull/pan w silniku
  (`src/reels_maker/iso/film.py`), przejścia między scenami
  czytelne, belki z opisami nie zasłaniają tematu.
