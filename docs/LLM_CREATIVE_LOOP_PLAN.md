# LLM Creative Loop — plan realizacji dla reels-maker

Data: 2026-11-13. Status: PLAN; wszystkie zadania LC pozostają nieodebrane.
Cel docelowego wdrożenia: main. Ten dokument nie wdraża funkcji ani nie
potwierdza przejścia testów. To szczegółowy podbacklog kreatywny MASTER_PLAN.md,
nie drugi nadrzędny master plan. ROADMAP_STATUS.json pozostaje historycznym
snapshotem do osobnego uzgodnienia; nie aktualizujemy jego dawnych liczników
ani statusów na podstawie samego napisania tego planu.

## 1. Decyzja produktowa

Produkt ma być reżyserem LLM z warsztatem wykonawczym, a nie katalogiem skryptów
lub szablonów. LLM odpowiada za koncepcję, metaforę/demonstrację, narrację,
kompozycję, choreografię, kamerę, dramaturgię dźwięku, porównanie wariantów i
rewizje. Python realizuje narzędzia, render, walidację, bezpieczeństwo i
reprodukowalność. Techniczny QA może odrzucić wykonanie; nie wybiera sam gustu.

Główne miary: preferencja właściciela w ślepym A/B, akceptacja pierwszej wersji,
liczba uwag artystycznych i rund do akceptacji, oryginalność adekwatna do briefu.
Rozdzielczość, bitrate, FPS i zielone testy nie zastępują tych miar. Nie ma
obietnicy, że każdy wynik będzie estetyczny lub zawsze nieszablonowy.

Carbon/Material/Fluent oraz receptury to narzędzia i referencje, nie granice
wyobraźni. Nowy preset sam w sobie nie jest postępem tego backlogu. Nie
wymuszamy sztucznej różnorodności, ruchu wszystkich warstw ani metryk liczby FX.
Nie kopiujemy cudzych ujęć, animacji, fontów, muzyki ani identyfikacji.

## 2. Stan wyjściowy i ponowne użycie

- Istnieją creative/spec.py, schema.py, compiler.py, pipeline_core.py,
  registry.py, director.py, edit.py, quality.py i reference_library.py.
  Rozszerzać ich kontrakty; nie tworzyć konkurencyjnego renderera.
- llm_muse.py jest małym klientem prompt -> tekst, nie pełnym orkiestratorem
  multimodalnym. Nie uznawać jego domyślnego endpointu za zweryfikowanego
  dostawcę; nie uruchamiano tutaj jego połączenia produkcyjnego.
- director.py ma heurystyki i wstępny wybór storyboardu; obecność tych funkcji
  nie dowodzi generowania pomysłów lub wizualnego gustu LLM.
- professional_direction.py i motionkit/carbon*.py są warsztatem wykonawczym.
  Receptura nie może po cichu zastąpić jawnego, poprawnego planu LLM.
- Carbon Choreography podłączono w commicie 490747d; nie powielać diagnozy
  o braku prepare_project/apply_project bez sprawdzenia aktualnego kodu.
  Pełne natywne testy/render ostatnich zmian nadal wymagają osobnego dowodu.
- PreferenceLibrary i LEARNINGS.md to zalążki pamięci, nie dowód trwałego
  uczenia gustu. Ponownie użyć istniejącego media/audio/data tooling i QA.
- Studio i Camera Canvas nadal mają odrębne ścieżki. Pierwszy pionowy prototyp
  LLM realizować na Studio; nie deklarować pełnej migracji wspólnego grafu.

Powiązania z master planem: LC-00 -> MD-001/206/305/406;
LC-01/07 -> MD-003/201/202; LC-03/05 -> MD-002/505;
LC-04/06/09 -> MD-508; LC-08/10 -> MD-404/406/510;
LC-11 -> MD-101..105/401/402; LC-13 -> MD-509;
LC-12 -> MD-003/201; LC-14/15 -> definicja odbioru i metryki master planu.
Nie oznaczać tych pakietów MD jako ukończonych tylko dlatego, że istnieje LC.

## 3. Docelowy przepływ

Brief + fakty + marka + uprawnienia + preferencje
 -> dobór kontekstu i legalnych referencji
 -> LLM: różne koncepcje wizualne
 -> LLM: art direction całego filmu
 -> LLM: otwarty plan scen i użycie narzędzi
 -> kompilator do istniejącego Studio -> twarde QA
 -> prawdziwe kadry i krótkie sekwencje z renderu
 -> krytyk multimodalny: ślepe porównanie + diagnoza
 -> LLM: poprawka lub zmiana koncepcji -> ograniczona pętla
 -> finalny film + ocena całości + decyzja właściciela
 -> trwała, kontekstowa pamięć feedbacku.

Trzy role logiczne: reżyser kreatywny, projektant-wykonawca, krytyk.
Nie muszą oznaczać trzech dostawców ani kilkunastu agentów. Oddzielić konteksty
oraz wejścia/wyjścia. Krytyk nie otrzymuje uzasadnienia autora ani jego nazwy;
nie nagradzać autora za przekonujący opis słabego obrazu.

## 4. Backlog — zakres, pliki, zależności i odbiór

Wszystkie ścieżki nowych modułów niżej są PROPOZYCJAMI, nie stanem wdrożenia.
P0 = pierwszy działający cykl kreatywny; P1 = rozszerzenie swobody i pamięci.

### LC-00 / P0 — zamrożenie bazy i kontrakt testowego renderu
- Zależności: brak. Sprawdzić bieżący commit, natywne testy Carbon i zwykłe
  Studio build, obsługę pełnego grafu oraz zgodność cache/przejść.
- Pliki: tests/test_carbon_*.py, studio_project.py, renderers/backend.py;
  dowody w dokumentacji, same media zgodnie z polityką repozytorium.
- Odbiór: odtwarzalny natywny MP4, raport faktycznie wykonanych testów i jawne
  braki. Nie zastępować tego samodzielnym Pillow/FFmpeg demonstratorem.
  Zamknąć błędy wykonawcze potrzebne do prototypu, nie rozbudowywać FX.

### LC-01 / P0 — kontrakty briefu i decyzji twórczych
- Zależności: brak; równolegle z LC-00.
- Nowe: creative/llm/contracts.py; rozszerzenia spec.py/schema.py/pipeline_core.py.
- Kontrakty: Brief, CreativeHypothesis, ArtDirection, SceneProgram,
  VisualCritique, RevisionPatch, PreferenceEvidence, RunLedger.
- Brief zawiera odbiorcę, cel, jedną główną myśl, potwierdzone fakty, CTA,
  markę, zasoby, ograniczenia i budżet. Nie wymaga gotowego scenariusza.
- Odbiór: walidowane JSON, stabilne ID, wersjonowanie i migracja v1;
  fakty/dane/licencje nie mogą być zmieniane przez artystyczną rewizję.

### LC-02 / P0 — rzeczywisty interfejs do modeli
- Zależności: LC-01.
- Nowe: creative/llm/providers.py, config.py; audyt llm_muse.py i .env.example.
  Najpierw zinwentaryzować również istniejące klienty/krytyków w iso/ i innych
  pakietach; adapterować nadające się elementy zamiast dublować integracje.
- Konfigurowalne aliasy modeli dla trzech ról, structured output, obraz,
  wideo/audio gdy obsługiwane, narzędzia, timeouty, retry, limity kosztu.
- Odbiór: mocki offline + osobny jawnie włączany test rzeczywistego dostawcy.
  Brak klucza lub zdolności vision ma dać błąd/ograniczenie, nie udawany wynik.
  Nie wybierać niezweryfikowanego endpointu ani zapisywać kluczy w repo.

### LC-03 / P0 — kontekst i reference retrieval
- Zależności: LC-01/02.
- Nowe: creative/llm/context.py; rozwój reference_library.py/reference_data.
- Dobierać niewielki, trafny kontekst według komunikatu, marki, formatu i
  intencji. Zwracać zasady, przykłady i antyprzykłady; nie cały katalog naraz.
- Odbiór: źródła i prawa przy każdym materiale, izolacja klientów, rozróżnienie
  obserwacji od hipotezy. Nie wymyślać obejrzanych ujęć i timecode'ów.

### LC-04 / P0 — generowanie koncepcji przez LLM
- Zależności: LC-01..03.
- Nowe: creative/llm/concepts.py i wersjonowane prompty.
- Początkowo trzy koncepcje: różne mechanizmy opowieści, nie trzy kolory/presety.
  Każda opisuje ideę, metaforę/demonstrację, scenę kluczową, przejście i ryzyka.
  LLM może odrzucić banalne kierunki i zaproponować nowy.
- Odbiór: właściciel rozpoznaje różnicę strategii; brak faktów wymyślonych dla
  efektu. Liczba i koszt wariantów konfigurowalne, nie dowód kreatywności.

### LC-05 / P0 — wizualny zestaw kalibracyjny
- Zależności: LC-03; budować równolegle z LC-04.
- Rozwój istniejącej biblioteki referencji i golden/reference manifests;
  nowe metadane przykładów, nie automatyczny import cudzych filmów.
- Zatwierdzone własne realizacje, legalne referencje, pary lepsze/slabsze oraz
  kontrolowane błędy kompozycji/ruchu. Notatki: dlaczego działa i kiedy nie.
- Odbiór: przykłady faktycznie ocenione przez człowieka, jawne źródła, podział
  kalibracja/test. Brak zatwierdzonych przykładów jest widocznym ograniczeniem.

### LC-06 / P0 — art direction całego filmu
- Zależności: LC-04; korzysta z LC-05 gdy są zaakceptowane przykłady.
- Nowe: creative/llm/art_direction.py; director.py jako interfejs, nie tabela gustu.
- LLM ustala motyw, hierarchię, typografię, relację obraz-tekst, kamerę,
  rytm napięcie/oddech i przejścia. Ma prawo wybrać nieruchomy kadr.
- Odbiór: decyzje spójne na poziomie filmu; bez automatycznego wymuszania
  różnych efektów w kolejnych scenach i bez identycznej receptury dla każdej marki.

### LC-07 / P0 — otwarty SceneProgram zamiast wyboru gotowej planszy
- Zależności: LC-00/01/06.
- Zmiany: compiler.py, registry.py, pipeline_core.py, components/, motionkit/;
  nowy creative/llm/tools.py, ewentualny SceneProgram v2 z adapterem v1.
- Udostępnić modelowi kompozycję tekstu, mediów, wektorów, masek, grup, kamery,
  ścieżek, zdarzeń i danych. Receptury to skróty, nie zamknięta lista wyników.
- Odbiór: LLM buduje scenę poza istniejącymi szablonami, używając tego samego
  grafu i renderera. Unsupported capability wraca do LLM jako luka do przeplanowania,
  nie jest po cichu zamieniana w statement/fade-up.
- Heurystyki pozostają jawnie oznaczonym fallbackiem; zapisywać decision_source
  llm/explicit/fallback. Kompilator nigdy sam nie wywołuje ukrytej sieci.

### LC-08 / P0 — materiał dowodowy z rzeczywistego renderu
- Zależności: LC-07.
- Rozwój storyboard.py i istniejących narzędzi render/QA;
  nowy creative/llm/evidence.py.
- Kadry do kompozycji, gęste próbki/klipy do wejść i przejść, cały klip do rytmu.
  Używać rzeczywistych zdjęć, wideo, fontów i warstw projektu, nie uproszczonych
  makiet tekstowych. Audio przekazywać tylko obsługującemu je modelowi.
- Odbiór: każdy dowód ma hash renderu i czas; różne podglądy nie mogą udawać
  zatwierdzonego finału. Brak oglądu ruchu/audio jawnie ogranicza werdykt.

### LC-09 / P0 — krytyk multimodalny i selekcja porównawcza
- Zależności: LC-02/05/08.
- Nowe: creative/llm/critic.py, ranking.py; zmiany director.py/quality.py.
- Porównywać pomysł, hierarchię, kompozycję, spójność, semantykę ruchu,
  oryginalność adekwatną do briefu i zgodność z gustem właściciela.
- Odbiór: anonimowe A/B, zamiana kolejności, remisy/niepewność, niezależny
  kontekst sędziego. Krytyka wskazuje widoczny problem, scene ID/timecode
  i wykonalną poprawkę; nie tylko ocenę 9/10 lub słowo premium.
  Kalibrować na ocenach człowieka, nie wyłącznie na sztucznych wadach.

### LC-10 / P0 — orkiestrator pętli kreatywnej i pionowy prototyp
- Zależności: LC-00..09, z minimalnym legalnym zestawem LC-05.
- Nowe: creative/llm/orchestrator.py, revisions.py; rozwój edit.py i cache;
  podłączenie cli_creative.py/cli_parser.py po weryfikacji aktualnych nazw plików.
- Proponowane polecenia, JESZCZE NIEISTNIEJĄCE: creative-generate,
  creative-review, creative-resume, creative-feedback.
- Odbiór: krótki brief -> koncepcje -> dwa rendery kluczowych momentów ->
  ocena -> poprawka -> pełny MP4. LLM może zmienić koncepcję, nie tylko font.
- Limit budżetu, retry i iteracji; na start proponowane max 3 rundy, do kalibracji.
  Zatrzymać przy stagnacji/regresji, zachować najlepszy legalny wariant,
  nie zwracać fikcyjnego sukcesu. Resume nie powtarza zapłaconych etapów.

### LC-11 / P1 — twórczy dobór mediów i dramaturgii audio
- Zależności: LC-06/07/10; użyć istniejącego asset brokera, audiokit i danych.
- LLM wybiera ujęcia, kadry, miejsca ciszy, akcenty/SFX i relację lektora do
  obrazu. Nie dodawać whoosha do każdego ruchu ani tekstu dublującego lektora.
- Odbiór: model uzasadnia wybór względem komunikatu, korzysta z dopuszczonych
  mediów i potwierdzonych danych. Nie może sam nadać nieznanym prawom approved.

### LC-12 / P1 — eksperymentalne komponenty tworzone przez LLM
- Zależności: LC-07/08/10; nie blokuje pierwszego działającego prototypu.
- Nowe: creative/llm/experiments.py, sandbox policy i testy izolacji.
- Gdy prymitywy nie wystarczają, model może zaproponować oryginalny komponent,
  geometrię/SVG lub kod komponentu. Najpierw eksperyment, nie automatyczna
  modyfikacja produkcyjnego silnika ani repozytorium.
- Odbiór: izolowany proces, brak sieci i sekretów, ograniczenia CPU/czasu/RAM/
  plików, allowlista zależności i walidacja wejść/wyjść. Sama kontrola AST
  nie jest sandboxem. Bez izolacji wykonanie kodu jest zablokowane.
  Awans do biblioteki wymaga osobnego przeglądu, testów i zgody.

### LC-13 / P1 — trwała pamięć gustu i rewizje bez ciągłego tłumaczenia
- Zależności: LC-05/09/10.
- Nowe: creative/llm/preferences.py i wersjonowany magazyn;
  integracja PreferenceLibrary/LEARNINGS.md bez dublowania prawdy.
- Zapisywać A/B, zaakceptowany wynik, korektę, kontekst i zakres: użytkownik,
  marka, kampania, projekt. Rozróżniać obserwację, hipotezę i twardą regułę.
- Odbiór: restart nie gubi decyzji; feedback wpływa na przyszłą selekcję;
  jedna korekta nie staje się zakazem globalnym. Konflikty, nowsze decyzje,
  usunięcie danych i kontrolowane eksperymenty mają jawne reguły.
  Nie przechowywać odrzuconych klipów wbrew obecnej polityce AGENTS.md;
  domyślnie metadane, wizualna retencja tylko po osobnej zgodzie/polityce.

### LC-14 / P0/P1 — benchmark kreatywności i estetyki
- Zależności: LC-05/09/10; definicję zestawu zacząć przed generowaniem wyników.
- Nowe: tests/creative_eval/ i raport porównań, osobno od testów pikselowych.
- Proponowany start: 8 briefów kalibracyjnych i 8 nowych testowych z kilku
  branż, w tym OZE. Ten sam brief, fakty, zasoby i budżet dla starej i nowej ścieżki.
- Odbiór: ślepy wybór człowieka, jawne N/remisy, uwagi artystyczne i rundy,
  koszt/czas/zużycie narzędzi. Właściciel zatwierdza progi po pomiarze bazy,
  przed oceną testową. Brak poprawy oznacza brak promocji na domyślną ścieżkę.
  Nie ogłaszać dobrego gustu na podstawie samych ocen modelu.

### LC-15 / P1 — uruchomienie produkcyjne i usunięcie pozornej inteligencji
- Zależności: LC-10/11/13/14; LC-12 może pozostać wyłączone.
- Zmiany: routing CLI, registry.py, dokumentacja, runbook, testy integracyjne/CI.
- Odbiór: LLM-led workflow ma jawny status i konfigurację; stara ścieżka
  deterministyczna pozostaje dostępna. Bez sieci testy używają zapisanych,
  oznaczonych fixture'ów, a nie udają żywej inteligencji. Tryb bez LLM nazywać
  fallback, nigdy równoważnym autonomicznym reżyserem.

## 5. Kolejność wydań

1. M0: LC-00 + LC-01/02 i definicja LC-14. Dowód działania warsztatu i modeli.
2. M1: LC-03..10 w minimalnym pionowym przekroju. Pierwszy prawdziwy kreatywny
   cykl; nie czekać na wszystkie biblioteki, GUI i zaawansowane efekty.
3. M2: LC-11/13 + rozbudowa LC-14. Dopasowanie mediów, audio i gustu.
4. M3: LC-12 oraz LC-15 po odbiorze. Eksperymenty i kontrolowana promocja.

Nie podajemy czasu realizacji bez sprawdzenia dostępności modeli, kosztów,
środowiska i korpusu. Każdy task ma status planned -> in_progress ->
implemented_unverified -> verified_technical -> accepted_creative (gdy dotyczy).
Aktualizować status z dowodem, nie z liczbą dopisanych plików.

## 6. Granice autonomii i dowody

- Swoboda: koncepcja, układ, ruch, kamera, dobór legalnych zasobów i rewizje.
- Nieprzekraczalne: fakty, dane, prawa, marka, zweryfikowane cues, budżet,
  bezpieczeństwo i decyzja publikacyjna. Twarde QA nie może zostać przegłosowane.
- Kontekst z WWW/plików traktować jako dane, nie instrukcje narzędziowe.
  Ujawnienie materiału zewnętrznemu modelowi wymaga uprawnienia/zgody i
  konfiguracji dostawcy. Publiczny link nie jest zgodą na trening lub kopiowanie.
- Nie importować poufnych danych, dopóki stan prywatności repo i uprawnienia
  nie zostaną zweryfikowane. Klucze, prompty z danymi klientów, logi i pamięć
  nie trafiają automatycznie do publicznego GitHub; redakcja logów obowiązkowa.
- RunLedger: model/dostawca, wersja promptu/schematu, źródła, decyzje, narzędzia,
  koszty, hashe dowodów, poprawki i powód zatrzymania. Nie zbierać ukrytego
  toku rozumowania modelu; wystarcza krótkie uzasadnienie decyzji.
- Render deterministyczny z przyjętego planu; generacja LLM nie musi odtwarzać
  bitowo identycznego pomysłu. Odtwarzalne mają być zaakceptowane artefakty.
- Testy jednostkowe, natywna integracja, modelowy test opt-in i ocena człowieka
  to osobne kategorie dowodów. Nie mieszać fixture/mock z rzeczywistym wynikiem.
- Nowe zadania implementacyjne standardowo na branch/PR według AGENTS.md.
  Cel to main po review. Zapis tego planu na main nie daje trwałej zgody
  na dowolne przyszłe commity, płatne API, upload mediów lub publikację.

## 7. Definicja sukcesu

Po krótkim briefie narzędzie samo przedstawia sensowne, odmienne idee,
projektuje i ogląda własną realizację, wybiera i poprawia ją na podstawie
obrazu/ruchu oraz trafniej uwzględnia gust właściciela. Potrzeba mniej
szczegółowych uwag artystycznych. Nie akceptujemy jako substytutu: większej
rozdzielczości, większej liczby presetów, dłuższego promptu lub zielonego CI.
