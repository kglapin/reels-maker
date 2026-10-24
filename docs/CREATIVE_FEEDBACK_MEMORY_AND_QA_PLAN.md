# Reels Maker — Creative Feedback Memory & Quality Gates
## Precyzyjny plan wdrożenia pamięci kreatywnej, polityk Do/Don't, oceny jakości i samonaprawy

**Wersja specyfikacji:** 1.0  
**Data:** 2026-10-24  
**Status:** PLAN — opis docelowego rozwiązania, nie deklaracja jego wdrożenia  
**Zakres:** globalny, marka, projekt, pojedynczy film/scena  
**Docelowy interfejs:** Python API + JSON-first CLI; później panel recenzenta  
**Zasada:** niniejszy dokument jest samodzielną specyfikacją. Nie zastępuje istniejącego MASTER_PLAN.md ani nie deklaruje wykonania jego zadań.

---

## 1. Cel produktu i kryterium sukcesu

Użytkownik podaje brief, stronę z ofertą, dane, multimedia lub scenariusz. Reels Maker produkuje film albo motion design z lektorem i po każdym przeglądzie może przyjąć uwagi wypowiedziane naturalnym językiem. System **zapamiętuje trwałe zasady, odróżnia je od jednorazowych poprawek, wykorzystuje przed każdą produkcją i sprawdza ich spełnienie przed oraz po renderowaniu**.

Przykładowe polecenie:

> „Nigdy nie dodawaj małych kickerów nad nagłówkami. Wyglądają jak AI slop. Jeśli kiedyś będę ich chciał, powiem o tym wyraźnie”.

Oczekiwany rezultat:
1. Interpreter wyodrębnia pojęcie: element graficzny typu kicker umieszczony nad głównym nagłówkiem.
2. Rozpoznaje trwały globalny zakaz stylistyczny z dopuszczonym wyjątkiem tylko na jednoznaczne polecenie właściciela.
3. Zapisuje **wersjonowaną, testowalną regułę**; przy niepewnym znaczeniu proponuje ją do zatwierdzenia.
4. Każdy nowy Creative Spec, Motion Plan i manifest jest filtrowany przez tę regułę; obecność niedozwolonego elementu zatrzymuje produkcję lub uruchamia bezpieczną korektę.
5. System sprawdza także wynikowy MP4, ponieważ sam poprawny manifest nie gwarantuje poprawnego obrazu.
6. Naruszenie tworzy raport i przypadek regresyjny. Po ponownym uruchomieniu programu polityka nadal obowiązuje.
7. Jednorazowy, wyraźny wyjątek „w tym klipie dodaj kicker” działa wyłącznie dla wskazanego klipu, jest audytowany i **nie kasuje globalnej reguły**.

### Niezmienniki (invariants)

- Żaden LLM nie może samodzielnie wyłączyć twardego walidatora ani nadpisać zatwierdzonej reguły.
- Nie wolno utożsamiać subiektywnej oceny modelu ze zweryfikowaną jakością profesjonalną.
- Krytyczne błędy liczb, licencji, bezpieczeństwa, marki, geometrii i publikacji nie mogą zostać „zaakceptowane” na podstawie wysokiej oceny estetycznej.
- Każda decyzja ma identyfikator źródła, wersję reguł, wersję specyfikacji, ślad audytowy i możliwą przyczynę.
- Naprawa zmienia możliwie mały fragment i nie może tworzyć nowych naruszeń.
- Reguły globalne muszą działać dla przyszłych nowych projektów i marek, nie tylko dla jednego szablonu.
- Wybór stylu i twórcza różnorodność pozostają możliwe **wewnątrz** zestawu ograniczeń.
- Dopóki weryfikacja nie jest rzeczywiście przeprowadzona, raport ma mówić „niezweryfikowano”, nigdy „zaliczone”.

## 2. Uczciwy punkt wyjścia w aktualnym repozytorium

Stan ustalony przez inspekcję głównej gałęzi z 2026-10-24:

| Istniejący element | Lokalizacja | Co można wykorzystać | Luka do zamknięcia |
|---|---|---|---|
| PreferenceLibrary | src/reels_maker/creative/director.py | Rejestrowanie wybranych preferencji kompozycji/ruchu | Wpisy są w pamięci procesu; brak trwałych globalnych zakazów, zakresów, rewizji i egzekucji |
| Creative Spec / walidacja schematu | creative/spec.py, creative/schema.py | Typowany kontrakt scen i elementów | Brak aktywnej polityki właściciela i walidacji relacji z trwałymi regułami |
| CreativeIntent → MotionPlan → RenderGraph | creative/pipeline.py | Naturalne miejsca wpięcia bramek | Brak zamrożonego snapshotu polityki i śledzenia naruszeń w całym łańcuchu |
| Director | creative/director.py | Heurystyczny dobór layoutu, ruchu i storyboardów | Oceny nie są modelem wyuczonych preferencji ani wiarygodnym ocenianiem estetyki |
| Natural-language edit | creative/edit.py | Bezpieczne poprawki po ID sceny | Obecnie obsługuje ograniczone wzorce poleceń anglojęzycznych; to nie interpreter polskich uwag |
| Referencje / antywzorce | creative/reference_library.py | Zasady warsztatowe i sygnały AI slop | Nie są prywatną, zmienianą przez właściciela pamięcią reguł |
| Kontrola kreatywna | creative/quality.py | Wczesne audyty scen, tekstu, rytmu i assets | Brak sprawdzania trwałych reguł oraz potwierdzania wszystkich warstw obrazu |
| Studio QA | qa/report.py | Geometria, safe areas, typografia, wartości, ograniczona naprawa | Należy podłączyć politykę oraz testy rzeczywistych klatek i czasu |
| Human review rubric | docs/REVIEW_RUBRIC.md | Dziewięć wymiarów odbioru ludzkiego | Brak automatycznej konwersji ocen i uwag na wersjonowane zasady |
| MASTER_PLAN.md | docs/MASTER_PLAN.md | Plan ogólny i wcześniejsze quality gates | Niniejszy dokument doprecyzowuje nowy subsystem, bez edycji planu ogólnego |

**Bieżący warunek operacyjny:** repozytorium jest PUBLIC; polityka projektu wymaga PRIVATE przed zapisaniem poufnych materiałów klientów. W repo wolno umieszczać tę ogólną specyfikację. Nie umieszczać tam rzeczywistych wypowiedzi klientów, nieopublikowanych filmów, danych ofertowych, tokenów ani zrzutów stron bez uprawnień. Prywatność, zgody i prawa do materiałów pozostają oddzielnymi bramkami wydania.

## 3. Architektura docelowa

    BRIEF / URL / DANE / MEDIA / LEKTOR
                        |
                        v
           Source & Facts Extractor
          (cytowane twierdzenia i prawa)
                        |
                        v
            Creative Intent / Plan
                        |
                [POLICY SNAPSHOT]
                        |
                        v
         GATE 1: Spec Policy Validator
                        |
                        v
               Motion Plan / Graph
                        |
                        v
         GATE 2: Structural QA / Layout
                        |
                        v
              Preview / Storyboard
                        |
                        v
         GATE 3: Rendered Preview QA
                        |
                        v
                Final Render MP4
                        |
                        v
        GATE 4: Encoded MP4 / Audio QA
                        |
                        v
           Human Review / Publication
                        |
              UWAGA UŻYTKOWNIKA
                        |
                        v
        Feedback Interpreter (LLM)
                        |
                        v
       Rule Proposal + Scope Resolver
                        |
                        v
     Approval/Conflict Check + Rule Store
                        |
                        +----> Nowa wersja POLICY SNAPSHOT
                        |
                        +----> Regression Case Library

### Moduły

**A. Feedback Capture.** Przyjmuje tekst, transkrypcję głosu, ocenę sceny, timecode, opcjonalny zaznaczony prostokąt i odniesienie do konkretnego renderu.

**B. Feedback Interpreter.** LLM zamienia mowę potoczną na propozycję strukturalną. Nie edytuje repo, reguł ani renderu bezpośrednio. W razie niepewności zwraca kilka interpretacji lub status wymagający potwierdzenia.

**C. Rule Registry / Creative Memory.** Trwała baza zasad: zakazy, nakazy, preferencje, pozytywne wzorce, wyjątki, wycofania, historia wersji, dowody, źródło decyzji.

**D. Policy Resolver.** Dla danego projektu oblicza dokładnie obowiązujący zbiór zasad oraz ich konfliktów. Wynik jest niemutowalnym artefaktem uruchomienia.

**E. Deterministic Policy Engine.** Sprawdza Creative Spec, manifest, typy elementów, właściwości motion, wartości, rozmiary i geometrię bez pomocy LLM tam, gdzie możliwe są jednoznaczne testy.

**F. Visual/Temporal QA.** Sprawdza rzeczywiście zdekodowane klatki MP4, zmiany pomiędzy klatkami, przebieg animacji, dźwięk i czytelność. Model wizyjny odpowiada za ocenę perceptualną, ale nie za twarde prawdy dotyczące geometrii i danych.

**G. Repair Planner.** Dobiera najmniejszą poprawkę, przedstawia jej przyczynę i mierzalny efekt, ponawia walidację i tylko potem renderowanie.

**H. Regression Library.** Zachowuje minimalne testy błędów oraz zaakceptowane przykłady wizualne; aktualizuje je wyłącznie po przeglądzie.

**I. Review Interface.** Umożliwia „zaakceptuj regułę”, „tylko ten klip”, „zapamiętaj na stałe”, „cofnij”, „pokaż, dlaczego odrzucono” i zatwierdzenie wyjątków.

## 4. Kategorie informacji zwrotnej

Każda uwaga jest klasyfikowana jednocześnie według **intencji, zakresu i charakteru egzekucji**.

| Typ | Przykład | Zachowanie |
|---|---|---|
| HARD_DONT | Nigdy nie dodawaj kickerów | Twardy zakaz w określonym zakresie |
| HARD_DO | Każdy wykres ma mieć prawdziwą jednostkę | Twardy wymóg |
| PREFERENCE | Wolę dłuższe, spokojniejsze ujęcia | Miękka preferencja przy wyborze kandydatów |
| APPROVED_PATTERN | Taka animacja licznika jest dobra | Preferowany wzorzec z dowodami i kontekstem |
| PROJECT_FIX | Popraw wykres w 3. scenie | Jednorazowy patch, bez tworzenia normy globalnej |
| TEMPORARY_EXCEPTION | Tylko tutaj zastosuj kicker | Wyjątek do konkretnego renderu; nie usuwa normy |
| NEGATIVE_EXAMPLE | Nie powtarzaj tego nieczytelnego wykresu | Antywzorzec z cechami wykrywalnymi i przykładem |
| FACT_CORRECTION | Kwota powinna być 12 000 zł | Poprawka danych oparta na zatwierdzonym źródle |
| RETRACTION | Cofnij moją poprzednią zasadę | Nowa rewizja dezaktywująca starą |
| QUESTION/AMBIGUOUS | To wygląda dziwnie | Brak automatycznego globalnego zakazu; zapytanie o znaczenie |

Zakresy: GLOBAL, BRAND, PROJECT, VIDEO, SCENE. Osobno należy przechowywać platformę (np. Reels) i kontekst zastosowania (np. wykresy, reklamy, materiały edukacyjne).

Przykład rozpoznania:
- „Nigdy / zawsze / w żadnym filmie” → kandydat na politykę globalną.
- „W filmach ASTA nie...” → polityka BRAND.
- „W tym filmie...” → VIDEO.
- „W trzeciej scenie...” → SCENE.
- „Nie podoba mi się” bez wskaźnika trwałości → poprawka lub propozycja preferencji; nie globalny zakaz.

Nie wolno automatycznie rozszerzać pojedynczej opinii o jednej scenie na wszystkie marki. Dwa identyczne komentarze nie tworzą dwóch sprzecznych reguł; system wykrywa duplikat i proponuje uaktualnienie dowodu.

## 5. Trwały model danych

### 5.1. Storage i wersjonowanie

Rekomendacja: SQLite z WAL dla pojedynczej instancji aplikacji (w standardowej bibliotece Pythona), oddzielne pliki dowodowe i eksport JSON do przenoszenia. Przy pracy wielu niezależnych workerów / użytkowników i intensywnych zapisach możliwa migracja na PostgreSQL przy zachowaniu repozytorium interfejsów.

Tabele:
- feedback_events — surowe wypowiedzi i metadane pochodzenia, nieedytowalne;
- rule_proposals — interpretacje LLM, dowody, poziom pewności, status;
- rules — identyfikator logiczny, typ, zakres, status, identyfikator bieżącej rewizji;
- rule_revisions — niemutowalne kolejne wersje;
- rule_exceptions — jednoznaczne odstępstwa dla wskazanych zadań;
- policy_snapshots — skompilowany zestaw aktywnych zasad, hash i źródła;
- qa_issues — naruszenia ze sceną, frame/timecode, dowodem i regułą;
- repair_attempts — poprawki, porównanie, wynik, koszty;
- review_decisions — zatwierdzenia człowieka i oceny;
- regression_cases — minimalne odtwarzalne przypadki i oczekiwany wynik;
- approved_patterns — dobre wzorce przypisane do konkretnego kontekstu.

Istotne pola audytu: rule_id, revision, actor, event_id, recorded_at (UTC), decision_at, source_render_sha256, spec_sha256, engine_version, schema_version, policy_sha256, previous_revision, reason.

Przechowywać oryginalne wypowiedzi i zanonimizowane wyciągi tylko przy odpowiednich zgodach. Lokalny plik bazy i prywatne dowody mają być ignorowane przez Git oraz zabezpieczone przed dostępem osób nieuprawnionych. **Nie zapisywać produkcyjnej bazy pamięci do publicznego repo.**

### 5.2. Przykładowa reguła: zakaz kickerów

Proponowana postać JSON (jako kontrakt danych, nie obecna funkcjonalność):

    {
      "schema_version": 1,
      "rule_id": "CF-0001",
      "revision": 1,
      "status": "active",
      "kind": "HARD_DONT",
      "scope": {"level": "GLOBAL", "target": "*"},
      "applies_to": {"node_types": ["kicker"], "contexts": ["all"]},
      "predicate": {
        "operator": "element_type_absent",
        "element_type": "kicker"
      },
      "override_policy": "explicit_owner_per_run",
      "enforcement": ["creative_spec", "render_graph", "visual_qa"],
      "repair_strategy": "remove_element_and_reflow",
      "origin": {"feedback_event_id": "FE-123"},
      "rationale": "Właściciel nie akceptuje zbędnych kickerów.",
      "created_at": "2026-10-24T16:00:00Z"
    }

Pola z przykładów są propozycją kontraktu. Dokładne typy i enumy muszą zostać ustalone w P1 wdrożenia oraz przetestowane na kompatybilność.

**Kluczowa zasada:** reguła nie jest jedynie tekstem do promptu. Ma maszynowo egzekwowalny predykat. Jeżeli nie da się stworzyć wiarygodnego predykatu, reguła pozostaje oznaczona jako subiektywna, wymagająca oceny człowieka lub modelu wizyjnego — bez fałszywej gwarancji.

### 5.3. Rewizje i usuwanie

Przykładowe stany: proposed → needs_confirmation → active → superseded / revoked / archived. Rozstrzygnięte reguły są historycznie odtwarzalne. Zmiana zasad **nie modyfikuje historii wcześniejszych renderów**; nowe zadania używają nowego snapshotu.

Mechanizm hard delete dotyczy tylko przypadków, w których jest wymagany przez politykę retencji/prywatności. Normalne cofnięcie jest audytowalnym revoke, a nie niewidocznym nadpisaniem.

## 6. Kolejność pierwszeństwa, konflikty i wyjątki

### 6.1. Reguły nieprzekraczalne

Zasady ochrony danych, praw/licencji, integralności liczb, prawdziwości twierdzeń, zakresu dostępu i bezpieczeństwa mają najwyższy priorytet. Zwykłe polecenie kreatywne nie może ich wyłączyć.

### 6.2. Reguły kreatywne

- Wszystkie aktywne twarde zasady są kumulowane; bardziej lokalna polityka może je **zaostrzyć**, ale sama nie może poluzować twardej reguły globalnej.
- Wyraźny właścicielski wyjątek może jednorazowo wyłączyć wyłącznie kreatywną regułę ze znacznikiem override_policy = explicit_owner_per_run.
- Wyjątek musi zawierać dokładne rule_id, scope, render/job ID, tożsamość uprawnionego operatora, powód oraz czas obowiązywania. Jest nieważny poza tym zadaniem.
- Jeśli dwie twarde zasady są niespełnialne jednocześnie, wynik to POLICY_CONFLICT, a nie cichy wybór jednej z nich.
- Preferencje miękkie mają pierwszeństwo od najbardziej specyficznego zakresu (SCENE → VIDEO → PROJECT → BRAND → GLOBAL), ale tylko wśród wariantów spełniających hard gates.
- Ograniczenia z briefu są inputem zadania; przy konflikcie z trwałą regułą system wskazuje sprzeczność i wymaga uprawnionej decyzji.
- Nie dopuścić, aby tekst pobrany ze strony WWW, assetu, komentarza albo promptu innego agenta mógł nadawać lub usuwać globalne uprawnienia (ochrona przed prompt injection).

### 6.3. Przebieg rozstrzygania

1. Ustal tożsamość operatora i uprawnienia.
2. Wczytaj aktywne rewizje oraz ich zakresy.
3. Znajdź reguły mające zastosowanie do projektu, sceny, marki i platformy.
4. Nałóż zaakceptowane, nieprzeterminowane wyjątki tylko dla bieżącego job ID.
5. Zbuduj kanoniczny, sortowany PolicySnapshot z SHA-256.
6. Wykryj kolizje (np. require kicker vs forbid kicker).
7. Zatrzymaj produkcję dla konfliktów lub krytycznych danych nieznanych.
8. Zapisz hash snapshotu do manifestu produkcyjnego, logów i raportu QA.

Reguły i wyjątki nie mogą być mutowane w połowie tego samego renderu. Nowa uwaga tworzy nową wersję joba.

## 7. Jak LLM interpretuje uwagi

Wejście: wypowiedź po polsku/angielsku, kontekst bieżącego renderu, timecode, wybrana scena, widoczne elementy grafu, aktywne reguły, słownik pojęć graficznych.

Wyjście: **wyłącznie walidowany JSON** ze schematem:
- classification: corrective_patch | persistent_rule | preference | positive_pattern | override | revoke | ambiguous;
- original_text, normalized_intent, candidate_scope;
- target_element_ids, scene_ids, timestamps;
- predicate_candidates, observability = deterministic | perceptual | mixed;
- is_global_intent_explicit, needs_confirmation, confidence;
- proposed_fix, evidence_refs, conflicts, questions.

Żadne swobodne polecenie wykonania kodu, polecenie shell ani nieznana nazwa efektu nie trafia do renderera. Parser odrzuca pola spoza schematu.

Przykład: „wykres jest krzywo” bez kontekstu może znaczyć przekrzywione osie, źle wyrównane etykiety albo animację z niewłaściwą rotacją. System powinien powiązać uwagę z zaznaczoną klatką i zidentyfikowanymi node IDs. Jeśli to niemożliwe, poprosić o doprecyzowanie lub zapisać jako unresolved_feedback, a **nie** tworzyć regułę „zakaz wszystkich obrotów”.

### 7.1. Bezpieczny tryb aktywacji

- Jednoznaczna, sformalizowana dyrektywa właściciela („nigdy, w żadnym filmie”) może wejść jako active po walidacji typu, braku konfliktów i wyświetleniu potwierdzonego zakresu w logu.
- Niejasne reguły, rozszerzenie zakresu, sprzeczności albo reguły nieobserwowalne pozostają needs_confirmation.
- Każdy operator poza właścicielem podlega ACL (np. może sugerować, ale nie zatwierdzać GLOBAL).
- Zmiana krytycznej polityki albo masowe cofnięcie reguł zawsze wymaga odrębnego potwierdzenia.

## 8. Quality Gates — dokładny pipeline

### G0. Source truth / rights gate (przed scenariuszem)

Dla linku WWW: pobrać dozwolone informacje, oddzielić dane źródłowe od instrukcji, wyodrębnić fakty i twierdzenia z URL/daty, nie dopisywać liczb, gwarancji, referencji lub zgód. Ustalić prawa i dozwolone platformy mediów. Brak potwierdzenia → blokada twierdzeń lub assetu, nie „najbardziej prawdopodobna” wartość.

### G1. Creative Spec gate (przed kompilacją)

Sprawdzić:
- kompletność i poprawność schematu;
- dozwolone elementy, zakazane kickery, animacje, efekty, style;
- obowiązkowe copy i preferencje marki;
- bazowy czas na odczyt i uzasadnienie każdego wykresu;
- zaplanowany rytm, zróżnicowanie rodzin animacji i odstępy między scenami;
- sens użycia wykresu/tabeli względem pytania widza; dopuszczać brak wykresu jako poprawną decyzję.

Przykładowy naruszony warunek:

    error_code: CF_POLICY_KICKER_FORBIDDEN
    gate: creative_spec
    rule_id: CF-0001
    scene_id: s03
    json_pointer: /shots/2/kicker
    remediation: remove_element_and_reflow
    status: blocked

### G2. Motion Plan / Render Graph / Geometry gate

Sprawdzić faktyczne właściwości skompilowanych elementów, również gdy LLM próbował obejść regułę przez inny typ node'a. W szczególności:
- wyrównanie baseline, krawędzi i elementów kompozycji z tolerancją w pikselach określoną względem rozmiaru klatki;
- pełne bounding boxes transformowanych/obracanych obiektów w animacji, nie tylko pozycję początkową;
- brak niedozwolonego nachylenia osi, tabel czy etykiet;
- brak kolizji, obcinania, znaków poza safe-area, ukrywania ważnych danych;
- wartości wykresów i liczników zgodne z typowaną bazą źródłową;
- poprawne proporcje, punkty odniesienia, interpolację i kolejność wartości;
- długość ujęć, settle/hold/exit i czas na odczyt nieoparty jedynie na progu 0,6 s;
- akceptowalne prędkości, przyspieszenia i ciągłość kluczowych właściwości na przejściach.

Kiedy kontrola geometrii jest rozstrzygalna, LLM nie może jej nadpisać oceną „wygląda w porządku”.

### G3. Preview / storyboard / actual frame QA

Zrenderować tylko próbki/sceny i ocenić **rzeczywiste piksele**:
- klatki start/koniec animacji, punkty zmiany easing, extrema, środek hold i miejsca przejść;
- próbki w przedziale ruchu; dodatkowo zagęszczać je przy szybkich obrotach i przejściach;
- OCR/wizję tylko pomocniczo do weryfikacji wyglądu, nie zamiast semantycznych identyfikatorów;
- model wizyjny porównuje pary wariantów i opisuje konkretne defekty, z odniesieniem do czasu i elementu.

Samo próbkowanie klatek nie wykrywa wszystkich artefaktów czasowych. Dla jittera, skoków pozycji, migania, przyspieszeń i problemów z wykresami wymagany jest pomiar klatka-po-klatce na krytycznym przedziale albo w pełnym wyrenderowanym zakresie.

### G4. Encoded MP4 + audio QA

Otworzyć rzeczywiście zapisany MP4 przez FFprobe/decoder. Sprawdzić:
- liczbę klatek, FPS, czas trwania, strumienie, błędy dekodowania;
- ramki i przejścia blisko szwów montażowych, czarne klatki, błyski, przesunięte maski;
- płynność wejść, wyjść, czytelną fazę ustaloną i brak nagłych cięć niezgodnych z planem;
- voiceover cues, napisy, opóźnienia, brak przyciętych słów;
- audio peak/clipping, loudness/ducking z odsłuchem tam, gdzie heurystyka nie wystarcza;
- prawidłowość wizualnych etykiet i reprezentację danych przez czas trwania animacji.

### G5. Human creative sign-off / publication gate

Użyć istniejącego docs/REVIEW_RUBRIC.md (hierarchia, typografia, ruch, rytm, obróbka obrazu, branding, audio, narracja, platforma). Eksport „technicznie poprawny” != „estetycznie zatwierdzony”. W szczególności dla filmów reklamowych: recenzja na telefonie z dźwiękiem, poprawność komunikatów i zatwierdzenie praw przed publikacją.

## 9. Wykrywanie AI slop — katalog testowalnych antywzorców

Nie tworzyć jednego nieinterpretowalnego „AI slop score”. Zamiast tego budować jawny katalog **cech obserwowalnych**, wskazując rodzaj dowodu:

| Antywzorzec | Sygnał i detektor | Konsekwencja |
|---|---|---|
| Zakazany kicker | Semantyczny node / pole kicker; kontrola grafu | Twarda blokada przy aktywnej regule |
| Zbędne efekty na każdym elemencie | Liczba unikalnych efektów, nieuzasadnione wejścia/wyjścia | Warning i propozycja uproszczenia |
| Zbyt krótkie ujęcia | Zmierzony reading load + długość settle/hold + lektor | Blokada lub warning zależnie od treści |
| Chaotyczne przejścia | Niespójność semantyki, prędkości, kierunku i liczby efektów | Kandydat do poprawy |
| Nieprawidłowe wykresy | Kontrola skali/zerowej bazy/znaku, sum, etykiet i przejść | Hard fail dla przekłamań |
| Źle wyrównane obiekty | Geometria po transformacjach, anchor/baseline/tolerancja | Hard fail, o ile reguła jednoznaczna |
| Nadmiar tekstu | Pomiar fontu, liczby linii, rzeczywistego czasu czytania | Hard fail dla obcięć |
| Fałszywy profesjonalizm (losowe ikony, blaski, ozdobniki) | Cel wizualizacji + stylistyczna spójność, ocena VLM | Soft/human gate, nigdy udawana pewność |
| Sztuczna powtarzalność | N-gramy layoutów, mechanizmów, timingów w obrębie filmu | Warning z kontekstową oceną |
| Niewłaściwa synchronizacja lektora | Word/phrase onsets, cue timeline vs frame onset | Blokada lub ręczny review przy braku dowodów |

Każdy detektor ma dokumentację: predicate, input, evidence, known_false_positives, known_false_negatives, severity, suggested_fix, tests, właściciel i numer wersji. Zakazy stylu muszą być powiązane z konkretnym typem obiektu, a nie jedynie zakazanym słowem w copy.

## 10. Pamięć pozytywnych wzorców

Niezależnie od DON'Ts system ma zapamiętywać DOs:
- zatwierdzony licznik z czytelnym easingiem i końcową fazą hold;
- zatwierdzony sposób animowania tabeli bez zmiany wartości i identyfikatorów wierszy;
- udane przejście pomiędzy ujęciami o określonej narracji;
- konkretny layout dla danych finansowych;
- tempo i rodzaj ruchu akceptowane dla danej marki.

Wzorzec zawiera: scenę, cel komunikacyjny, rodzinę motion, dane wejściowe, screenshoty/fragment zatwierdzonego renderu (w prywatnym magazynie), ocenę człowieka, obowiązujący brandbook i warunki użycia.

**Nie kopiować mechanicznie jednego filmu.** Director powinien wybierać spośród zatwierdzonych receptur z karą za monotonność i z uzasadnieniem: „dobrano wariant X, ponieważ scena porównuje wartości i wymaga stabilnych etykiet”. Zatwierdzone fragmenty klientów muszą respektować prawa i zakres ponownego wykorzystania.

## 11. Zamknięta pętla samonaprawy

Protokół:

1. Wygeneruj PolicySnapshot oraz CreativeSpec.
2. Uruchom G0–G2.
3. Błąd deterministyczny: dołącz rule_id, node_id i najmniejszą możliwą zmianę.
4. Wybierz poprawkę z bezpiecznych transformacji (np. usuń kicker i przelicz layout; zwiększ hold; zamień nieczytelny wykres na tabelę).
5. Zapisz patch do **nowej wersji** specyfikacji, bez zmiany reguł i surowych danych.
6. Uruchom ponownie wszystkie bramki dotknięte patchem.
7. Zrenderuj tylko zależne sceny, jeśli pipeline/cache gwarantuje identyczny wynik reszty.
8. Sprawdź rzeczywisty MP4 po połączeniu; porównaj przed/po.
9. Przyjmij poprawkę wyłącznie jeśli źródłowy błąd zniknął i nie powstało nowe krytyczne naruszenie.
10. Po maksymalnie trzech automatycznych próbach na ten sam problem zakończ jako BLOCKED / NEEDS_HUMAN_REVIEW z konkretnymi dowodami, nie jako sukces.

Reguły praw, licencji, danych, faktów oraz ostatecznej zgody publikacyjnej nie mogą być „naprawiane” przez fabrykowanie źródeł albo obniżanie progu weryfikacji.

### Zasada izolacji

Zmiana jednej sceny nie powinna przypadkowo zmieniać kolejności ujęć, całej kolorystyki czy charakteru poprzednich zaakceptowanych sekwencji. Zmiany globalne wymagają osobnej intencji. Nazwane sceny i obiekty mają stałe ID, a cache wykorzystuje zależności (asset + manifest + polityka + wersja silnika).

## 12. Kontrakty CLI/API — projektowane, NIE obecnie dostępne

Przykładowy interfejs JSON-first:

    reels-maker feedback add --job JOB_ID --scene s03 --time 00:08.20 --text "Nigdy nie dodawaj kickerów" --json
    reels-maker feedback proposals --status needs_confirmation --json
    reels-maker feedback approve CF-0001 --scope GLOBAL --json
    reels-maker feedback revoke CF-0001 --reason "zmiana wytycznych" --json
    reels-maker policy effective --brand asta-energy --project VIDEO.json --json
    reels-maker policy check VIDEO.json --stage creative_spec --strict --json
    reels-maker review run JOB_ID --profile review --json
    reels-maker review issues JOB_ID --json
    reels-maker repair JOB_ID --issue QA-XXXX --max-attempts 3 --json
    reels-maker regression run --suite creative-policy --json

Każda komenda musi mieć określone exit codes:
- 0: operacja poprawna / walidacja zaliczona;
- 2: invalid request / schema;
- 3: policy violation / conflict;
- 4: niezweryfikowany zewnętrzny warunek;
- 5: prawa/bezpieczeństwo blokują dalszy etap;
- 6: nieusunięty błąd QA;
- 7: brak uprawnienia;
- 8: błąd renderera / wykonania.

Wynik nie może kończyć się na {"ok": true}; ma zawierać checked_rules, unchecked_rules, violations, warnings, policy_sha256, render_sha256 (jeśli istnieje), evidence_refs, next_action i human_review_required.

Proponowane API Pythona:
- capture_feedback(event, context) -> FeedbackEvent
- interpret_feedback(event, snapshot) -> RuleProposal
- approve_rule(proposal_id, actor) -> RuleRevision
- resolve_policy(job) -> PolicySnapshot
- audit_spec(spec, policy) -> GateResult
- audit_render_graph(graph, policy) -> GateResult
- audit_encoded_video(mp4, graph, policy) -> GateResult
- plan_repair(issue, context) -> RepairProposal
- run_regression_suite(rule_id=None) -> TestReport

## 13. Integracja z kodem — projekt plików

Wszystkie poniższe ścieżki są **planowane**, a nie już utworzone w tym zadaniu:

    src/reels_maker/creative_memory/
        __init__.py
        models.py                # enumy, typowane kontrakty, JSON Schema
        store.py                 # SQLite, transakcje, migracje, historie rewizji
        interpreter.py           # LLM -> RuleProposal, parser z polskim językiem
        resolver.py              # scope, uprawnienia, konflikty, polityka effective
        predicates.py            # rejestr twardych, deterministycznych walidatorów
        preflight.py             # G1, G2, policy gates
        visual_review.py         # G3/G4, wybór klatek i model wizyjny
        temporal_review.py       # frame-to-frame / motion / transition diagnostics
        repair.py                # bezpieczne transformacje i limity prób
        positive_patterns.py     # zaakceptowane receptury
        regressions.py           # katalog testów i fixtures
        reporting.py             # raport QA i dowody
    tests/
        test_creative_memory_models.py
        test_creative_memory_store.py
        test_creative_memory_interpreter.py
        test_creative_memory_resolver.py
        test_creative_memory_preflight.py
        test_creative_memory_visual_review.py
        test_creative_memory_repair.py
        test_creative_memory_regressions.py
    docs/
        CREATIVE_FEEDBACK_MEMORY_AND_QA_PLAN.md  # ta specyfikacja

Miejsca integracji:
1. creative/schema.py + spec.py — obsługa rozpoznawanych elementów i reguł przez **zewnętrzną** policy layer (bez mieszania historii użytkownika ze schematem filmu).
2. creative/director.py — miękkie preferencje i dobór pozytywnych wzorców; zastąpienie wyłącznie procesowej PreferenceLibrary adapterem do trwałej bazy.
3. creative/pipeline.py — policy snapshot przed CreativeIntent, następnie bramki przy MotionPlan i RenderGraph.
4. creative/quality.py + qa/report.py — naruszenia reguł z ID, dowodami i severity; nie dublować istniejących kontroli geometrii.
5. creative/edit.py — wykorzystać bezpieczny JSON Patch i identyfikatory scen; interpreter polskiego dodać osobno.
6. cli.py — nowe komendy, zgodne z obecnym JSON-first CLI; renderer legacy i Studio zachowują działanie, gdy nowe funkcje są wyłączone.
7. docs/REVIEW_RUBRIC.md — **wykorzystać bez edycji** jako wejście człowieka; skale 0–4 pozostają jawne.
8. Testy renderów / golden frames — budować obok istniejących, a nie nadpisywać ich bez recenzji.

Nie wprowadzać nowego niezależnego renderera. Wszelkie reguły muszą działać zarówno na obecnych ścieżkach legacy, jak i Studio / Camera Canvas zgodnie z ich rzeczywistymi możliwościami. Brak obsługi konkretnej bramki w rendererze → wynik UNCHECKED, nie PASS.

## 14. Strategia testowania i mierzenia skuteczności

### 14.1. Jednostkowe i kontraktowe

- zapis reguły → restart procesu → ponowny odczyt tej samej wersji i zakresu;
- idempotentny import tej samej uwagi;
- regresje schematu JSON, brak nieznanych pól, ochrona przed injection;
- globalny HARD_DONT blokuje odpowiednie elementy we wszystkich markach;
- wyjątek jednorazowy dopuszcza tylko wybraną regułę w jednym jobie;
- niedozwolony override bezpieczeństwa i danych jest odrzucany;
- revocation pozostawia niezmienioną historię starych renderów;
- konflikt HARD_DO i HARD_DONT kończy się BLOCKED;
- utrata SQLite/transakcji nie prowadzi do częściowo zaakceptowanej reguły;
- pomyłka klasyfikatora nie może tworzyć niezauważonych reguł globalnych.

### 14.2. Konkretne przypadki kreatywne

**Test KICKER:** globalny zakaz. Generate 20 zróżnicowanych projektów; w każdym pole kicker albo semantyczny odpowiednik musi zostać odrzucony przed renderem. Osobny test: jednoznaczny wyjątek dopuszcza element w tym jednym zadaniu, bez wpływu na kolejny film.

**Test ALIGNMENT:** scena z nieprawidłowo obróconymi etykietami i poprawna scena z celowym pochyleniem artystycznym. Sprawdzić false positives i typy semantyczne; nie blokować wszystkich rotacji z automatu.

**Test CHART TRUTH:** dodatnie, ujemne i zerowe wartości, brakujące dane, zmienna skala, procenty, animowane rankingi i liczniki. Brak przekłamań w żadnym kroku animacji.

**Test RHYTHM:** 6–12 scen z lektorem o różnym tempie; minimum czasu odczytu, płynne granice, brak zbędnego przyspieszania i zamrażania przypadkowych klatek.

**Test FEEDBACK UNDERSTANDING:** polskie formy odmienne, zaprzeczenia, ironia, wskazanie sceny, „tylko ten film”, „nigdy”, „zawsze”, prośba o cofnięcie, dwa sprzeczne polecenia i niejednoznaczne „krzywo”.

**Test VISUAL:** approved / rejected pairs, kontaktowe klatki i krótkie odcinki MP4 w różnych formatach. Wyniki VLM porównywać z ręcznie opisanymi naruszeniami; brak dowodu nie oznacza zaliczenia.

**Test REPAIR:** minimalny patch, maksymalnie 3 próby, niezmienione sąsiednie sceny, pełne ponowne sprawdzenie finalnego MP4.

### 14.3. Proponowane KPI odbioru

- 100% wykrytych w testach kontraktowych naruszeń maszynowo reprezentowalnych twardych reguł (na kompletnym syntetycznym zestawie testów).
- 0 znanych przypadków cichego pominięcia polityki po restarcie lub pomiędzy renderami.
- 0 zaakceptowanych bez jawnej zgody globalnych reguł z niejednoznacznych wypowiedzi.
- 100% raportów ze śladem rule_id, policy hash i informacją, które warstwy rzeczywiście sprawdzono.
- 0 nieautoryzowanych wyjątków od zasad bezpieczeństwa, praw mediów i danych.
- Żadna „poprawka” nie przechodzi, gdy tworzy nowy krytyczny błąd.
- Wyniki klasyfikacji wypowiedzi i VLM: mierzyć precision, recall oraz odsetek fałszywych alarmów na ręcznie ocenionym zbiorze; progi produkcyjne zatwierdzić po pilotażu, nie deklarować ich bez pomiaru.
- Ocena craft: porównanie A/B przez człowieka względem dotychczasowego Reels Makera; nie sprowadzać do arbitralnej jednej liczby.

## 15. Kolejność wdrażania i warunki odbioru

### P0 — fundament bezpieczeństwa i kontraktów

Zakres:
- zinwentaryzować aktualne przepływy Creative Spec/Studio/Legacy i istniejące QA;
- potwierdzić prywatność repo oraz bezpieczne miejsce na bazę i załączniki;
- ustalić typy i rozstrzygalne predykaty, poziomy uprawnień, reguły override;
- przygotować 30–50 przykładowych polskich uwag i ich oczekiwane interpretacje;
- spisać rozstrzygnięcia słownika: kicker, subtitle, title, caption, callout, data label.

Odbiór: zatwierdzone kontrakty, schemat i threat model, bez zmiany renderów.

### P1 — trwała pamięć i feedback parser (MVP)

Zakres:
- SQLite, migracje, immutable events, eksport;
- parser feedbacku z modelem LLM i walidacją odpowiedzi;
- approve/revoke, scope, snapshot, uprawnienia, CLI;
- testy restartów, konfliktów, retencji i polskich poleceń.

Odbiór: wypowiedziane „nigdy nie dodawaj kickerów” zapisuje się poprawnie, nie znika po restarcie i może zostać jawnie wycofane.

### P2 — deterministyczne quality gates (najważniejszy etap)

Zakres:
- skompilowane effective policies dla joba;
- walidator elementów, danych, geometrii, typografii, scen i timingów;
- integracja Creative Intent → Motion Plan → Render Graph;
- raporty z identyfikatorami i blokada niedozwolonego renderowania.

Odbiór: zakazany element **nie może trafić do produkcyjnego MP4**, bez względu na to, czy wpisał go LLM, szablon czy inny etap kompilacji.

### P3 — multimodalny recenzent i naprawa

Zakres:
- analiza wybranych klatek i odcinków prawdziwego MP4;
- detektory czasowe, przejścia, wykresy, audio; structured VLM issues;
- do 3 prób samonaprawy z rerenderem zależnych scen i QA finalnego pliku;
- dowody w postaci klatki/timecode, porównanie przed/po i jawne ograniczenia.

Odbiór: sceny z rzeczywistymi błędami są poprawiane albo blokowane, a nie bezwarunkowo zatwierdzane przez model.

### P4 — pozytywne wzorce i personalizacja

Zakres:
- katalog zaakceptowanych receptur z kontekstem ich użycia;
- preferencje globalne i brand-specific dla directora;
- inteligentne dobieranie wariantów bez monotonnej powtarzalności;
- A/B human ratings; monitorowanie drifu jakości.

Odbiór: na reprezentatywnym zestawie testów człowiek wybiera nowy pipeline częściej niż bazowy; jednocześnie nie ma wzrostu naruszeń twardych zasad.

### P5 — pełna produkcja z linku

Zakres (integracyjny, nie implementacja scrapera w tej specyfikacji):
- źródła URL, fact sheet, claim evidence, legal rights;
- LLM Story Director generuje 3 warianty narracji;
- polityka kreatywna i referencje ograniczają kandydatów przed renderem;
- render / kontrola / korekty / human sign-off.

Odbiór: trzy różne oferty i trzy różne style przechodzą cały pipeline w odtwarzalnych jobach, z udokumentowanymi źródłami, prawami, regułami i wyjątkami.

## 16. Definicja ukończenia (Definition of Done)

Podsystem można nazwać gotowym do produkcji dopiero gdy:
1. Przyjmuje polskie uwagi głosowe/tekstowe i rozróżnia trwałą regułę od doraźnej poprawki.
2. Zachowuje reguły, rewizje, zakresy, wyjątki i audyt między restartami.
3. Egzekwuje HARD_DONT i HARD_DO deterministycznie tam, gdzie reguły są formalnie sprawdzalne.
4. Blokuje niezgodne z polityką sceny przed renderowaniem albo naprawia je bez obchodzenia walidacji.
5. Waliduje rzeczywisty MP4 i dźwięk, a nie tylko JSON/preview.
6. Zachowuje dowody naruszeń, timecode, object ID i używaną wersję polityki.
7. Ma regresje od każdego krytycznego zgłoszonego błędu.
8. Ma kontrolowane, jednorazowe odstępstwa kreatywne i brak odstępstw od zasad krytycznych.
9. Potrafi zgłosić brak pewności, przekazać sprawę człowiekowi i zatrzymać proces.
10. Został przetestowany na różnych markach, wykresach, tabelach, formatach, polskich znakach, montażu wideo i motion designie.
11. Ma niezależną ocenę człowieka na telefonie z dźwiękiem; model wizyjny jest wsparciem, nie certyfikatem jakości.
12. Nie wycieka z lokalnej/poufnej bazy do publicznego repozytorium.

## 17. Decyzje architektoniczne — zalecany wariant

**Wybrać:** Python + obecny renderer / Studio + SQLite (z opcją późniejszej migracji) + typowane predykaty + policy snapshot + zewnętrzny LLM do interpretacji + niezależne visual QA + regresje.

**Nie wybierać:** samego pliku z promptem „Do's and Don'ts” jako jedynej pamięci; dowolnego wykonywania kodu wygenerowanego przez LLM; automatycznego ustanawiania globalnych zasad z niejednoznacznej uwagi; nagradzania estetyki jednym nieprzejrzystym wskaźnikiem; samonaprawy bez limitu; automatycznego obniżania progów QA; umieszczania materiałów recenzenckich w publicznym Git.

**Kolejność wartości:** P1 (pamięć) + P2 (egzekucja) należy wdrożyć **przed** P3 (wizyjna samokrytyka), bo sam model wizyjny nie zagwarantuje przestrzegania jawnych wymagań użytkownika.

## 18. Ślad powiązania z obecnymi standardami projektu

Zachować i wykorzystywać bez tworzenia konkurencyjnych źródeł prawdy:
- docs/MASTER_PLAN.md — strategiczny backlog i ogólny pipeline;
- docs/ROADMAP_STATUS.json — stan aktualnych zadań, nie dowód ukończenia niniejszej nowej specyfikacji;
- docs/REVIEW_RUBRIC.md — kryteria człowieka;
- docs/REFERENCE_LIBRARY.md i creative/reference_library.py — źródła dobrych praktyk i antywzorców;
- docs/PRO_TYPOGRAPHY_SYSTEM.md — obowiązujący system czytelności;
- docs/DATA_MOTION_DESIGN.md — domenowe wytyczne animowania danych;
- AGENTS.md — zasady pracy na repozytorium, szczególnie prywatność, prawa i review;
- src/reels_maker/qa/report.py — istniejący system dowodów technicznych.

Niniejszy dokument **nie modyfikuje** tych plików i celowo stanowi kompletny, samodzielny plan jednego nowego subsystemu. Realizację należy prowadzić małymi, testowalnymi zmianami z oddzielnymi commitami; każda faza musi mieć działający kontrakt, testy, faktyczne dowody i jasną informację, czego nadal nie sprawdzono.
