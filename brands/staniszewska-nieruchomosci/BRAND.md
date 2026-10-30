# Staniszewska Nieruchomości — brandbook roboczy

Wersja 1.0 · 26 października 2026 r.  
Źródło: [staniszewskanieruchomosci.pl/oferty](https://staniszewskanieruchomosci.pl/oferty/?sn_action=na-sprzedaz) oraz [strona „O nas”](https://staniszewskanieruchomosci.pl/o-nas/).

## Status i podstawa opracowania

To robocze wytyczne do tworzenia materiałów wideo i digital dla marki Staniszewska Nieruchomości. Opierają się na publicznie widocznej stronie ofert i deklarowanym tam sposobie obsługi: lokalnie, spokojnie, rzeczowo i z dbałością o szczegóły.

Kolory poniżej są przybliżonym odwzorowaniem widocznej strony, a nie wartościami potwierdzonymi w oficjalnej księdze znaku. Inter pozostaje wyłącznie rekomendacją wizualną: dostępne materiały nie potwierdzają, że strona deklaruje ten krój w CSS. Nie opisuj Inter jako fontu marki, dopóki nie potwierdzi go arkusz stylów lub właściciel. Oficjalny biały wariant logo został dostarczony przez użytkownika i zapisany w `media/assets/`; używaj go na ciemnym tle.

## 1. Charakter marki

**Rola:** lokalne biuro nieruchomości prowadzące klientów przez sprzedaż, kupno i wynajem, z pomocą w finansowaniu.

**Obietnica komunikacyjna:** przejrzysty proces, konkretna informacja i spokojne wsparcie przy ważnej decyzji dotyczącej nieruchomości.

**Cechy marki:** lokalna, uważna, kompetentna, uporządkowana, dostępna.

**Wrażenie wizualne:** nowoczesna elegancja bez nadęcia. Ciepłe złoto wyróżnia istotne elementy, ciemny grafit buduje kontrast i poczucie stabilności, a jasne tła utrzymują oferty w roli głównej.

### Ton komunikacji

- Pisz spokojnie, konkretnie i po polsku. Zwracaj się bezpośrednio do odbiorcy.
- Najpierw podaj praktyczną informację lub kolejny krok; dopiero potem opisuj korzyść.
- Nazywaj lokalizację i rodzaj nieruchomości. Parametry podawaj jasno, z jednostkami.
- Unikaj presji, pustych superlatywów, obietnic ceny lub terminu sprzedaży oraz niepotwierdzonych statystyk.
- Nie przedstawiaj informacji prawnych, planistycznych ani finansowych jako pewnych, jeśli wymagają indywidualnej weryfikacji.
- Nie dodawaj emoji ani ozdobnych wykrzykników.

**Przykładowy kierunek nagłówków:** „Szukasz domu w Kaliszu?”, „Działka z dojazdem od dwóch ulic”, „Zobacz, co warto sprawdzić przed zakupem”. To przykłady tonu, nie potwierdzone oferty ani obietnice.

## 2. Paleta kolorów

| Rola | Wartość robocza | Zastosowanie |
| --- | --- | --- |
| Ciepłe złoto | `#D8A356` | Małe akcenty, wyróżnione ceny, znaczniki, krótkie linie i elementy CTA |
| Grafit | `#171C22` | Ciemne plansze, stopki, belki i tekst na jasnym tle |
| Biel | `#FFFFFF` | Tło ofert, jasne plansze, przestrzeń i kontrast |
| Jasny szary | `#F4F5F6` | Panele parametrów, neutralne karty i drugorzędne tła |
| Szary tekstowy | `#68717A` | Opisy pomocnicze, metadane i podpisy |
| Obramowanie | `#E3E6E9` | Delikatne krawędzie kart i separatorów |

**Użycie:** złoto ma prowadzić wzrok, nie wypełniać całych plansz. Na złotym tle używaj ciemnego tekstu; biel na złocie może mieć zbyt niski kontrast w małych rozmiarach. Na jasnym tle stosuj grafitowy tekst, na ciemnym — biały. Weryfikuj czytelność po eksporcie na ekranie telefonu.

## 3. Typografia

- **Kierunek:** nowoczesny, czytelny bezszeryfowy krój o neutralnym charakterze.
- **Rekomendacja robocza:** Inter jako neutralny krój wizualny do prototypów. Nie jest potwierdzoną rodziną fontu ze strony ani zatwierdzonym fontem marki.
- **Fallback renderera:** DejaVu Sans.
- Nagłówki składaj średnią lub pogrubioną odmianą. Treść i dane pomocnicze — regularną.
- Wielkie litery rezerwuj dla krótkich etykiet. Unikaj długich wersalików i nadmiernego rozstrzelenia.
- Pilnuj polskich znaków, naturalnych podziałów wierszy i czytelnych liczb: `140 m²`, `350 zł/m²`, `62-800 Kalisz`.
- Nie osadzaj ani nie dystrybuuj fontu, dopóki jego plik i licencja nie zostaną potwierdzone.

## 4. Logo

Zapisany znak to biały wariant poziomy 300 × 78 px: złoty monogram, jasny napis „STANISZEWSKA” i mniejszy podpis „NIERUCHOMOŚCI”. Źródło: plik z oficjalnej strony wskazany przez użytkownika. Oryginał WebP i kopia PNG wymagane przez renderer znajdują się w `media/assets/`.

- Używaj wyłącznie oficjalnego pliku dostarczonego przez właściciela marki, najlepiej SVG oraz PNG z przezroczystością.
- Zachowaj proporcje, odstęp ochronny i czytelność małego podpisu. Nie zmieniaj kolorów ani nie dodawaj efektów.
- Na jasnym tle użyj oficjalnego wariantu przeznaczonego na jasne tło. Jeśli go nie ma, pozostaw miejsce na znak zamiast samodzielnie przerabiać logo.
- Nie przerysowuj monogramu i nie wycinaj logo ze zrzutu strony.
- Nie używaj tego białego wariantu na jasnym tle ani w jasnych profilach animacji.

`branding.logo` wskazuje lokalny PNG. W presetach jest aktywny wyłącznie profil `property-story-dark`; profile jasne pozostają bez logo.

## 5. Fotografia i ilustracje

- Pierwszeństwo mają autentyczne, aktualne zdjęcia przedstawianej nieruchomości.
- Pokazuj różnorodne oferty: mieszkania, domy i działki. Nie sugeruj, że marka obsługuje wyłącznie segment premium.
- Wybieraj naturalne światło, spokojne kadry, poprawną geometrię wnętrz i czytelny kontekst lokalizacji.
- Zdjęcia z drona wykorzystuj do pokazania położenia działki lub otoczenia, nie jako dekoracyjne tło bez informacji.
- Nie zmieniaj cech nieruchomości, widoku, sąsiedztwa ani stanu technicznego. Nie usuwaj wad i nie dodawaj elementów, których nie ma.
- Materiały stockowe mogą ilustrować poradnik lub ogólny temat, ale nie mogą udawać konkretnej oferty.
- Do każdego obrazu, klipu i utworu wymagaj udokumentowanych praw oraz zgody na użycie w danym kanale. Nie wykorzystuj automatycznie zdjęć pobranych ze strony.

## 6. Kompozycja i ruch w Reels

- Pokaż jedną nieruchomość lub jedną praktyczną myśl na scenę. W pierwszej chwili nazwij temat albo lokalizację.
- Poruszaj kamerą i elementami oszczędnie: łagodne przesunięcie, delikatny najazd, spokojne odsłonięcie informacji. Przejście nie powinno odwracać uwagi od oferty.
- Parametry grupuj w czytelne moduły; nie zamieniaj planszy w gęstą tabelę. Cenę i metraż wyróżniaj typografią, a złoto stosuj punktowo.
- Zakończ prostym, nienachalnym krokiem: „Zadzwoń i umów prezentację”, „Zapytaj o szczegóły” albo „Sprawdź ofertę”. Dane kontaktowe dodawaj tylko wtedy, gdy są aktualne i mieszczą się w bezpiecznym obszarze.
- Zachowaj naturalne tempo i krótkie pauzy, aby odbiorca zdążył przeczytać lokalizację, cenę i kluczowe parametry.
- Nie dodawaj statystyk, opinii klientów, gwarancji ani informacji o dostępności bez aktualnego źródła i zgody na publikację.

### Pionowy format 9:16

Wszystkie teksty i ilustracje pierwszego planu pozostają wewnątrz fioletowego obszaru bezpieczeństwa wskazanego w projekcie. Pomarańczowy obszar jest marginesem. Poza fioletowy obszar mogą wychodzić wyłącznie tła oraz przesunięcia elementów w trakcie animacji, zgodnie z ogólną regułą projektu. Sprawdzaj również klatki pośrednie i końcowe; nie zmniejszaj czytelności, aby zmieścić zbyt długi tekst.

## 7. Stałe zasady dla projektów

- Manifesty zapisuj w `brands/staniszewska-nieruchomosci/projects/`.
- Powtarzalny styl filmów do Stories opisuje [szablon Stories](templates/stories-style-template.md).
- Zdjęcia, klipy, logo, fonty i audio trzymaj w katalogu tej marki; nie dodawaj ich do kodu silnika.
- Każdy materiał zewnętrzny wpisz do `licensing/` ze źródłem, autorem, licencją, zakresem użycia i datą sprawdzenia.
- Nie traktuj nieweryfikowanych materiałów z `imports/` jako zatwierdzonych do publikacji.
- Po utworzeniu projektu sprawdź geometrię i teksty w storyboardzie oraz odtwórz MP4 z dźwiękiem. Kontrola techniczna nie zastępuje akceptacji właściciela marki.

## 8. Do potwierdzenia przed zatwierdzeniem identyfikacji

1. Pozostałe warianty logo oraz zasady pola ochronnego; obecny plik to biały wariant do ciemnego tła.
2. Dokładne wartości HEX z arkuszy CSS lub księgi znaku.
3. Rodzina i dostępne grubości fontów oraz licencja na użycie w materiałach.
4. Zasady uzyskiwania zgód na zdjęcia nieruchomości, wnętrz i wizerunku osób.

Do czasu potwierdzenia tych elementów traktuj `brand.json` jako roboczy preset cyfrowy, a nie kompletną, oficjalnie zatwierdzoną księgę znaku.
