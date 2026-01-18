# Orzecznictwo — instrukcje użycia wyszukiwarek (SN / TK / NSA / Sądy powszechne)

Cel: umożliwić PrawoL (custom GPT) szybkie znalezienie właściwych orzeczeń **bez utrzymywania pełnej lokalnej bazy**.  
Zasada: **ELI (Dz.U.) jest kotwicą** → z ELI wyciągamy tytuł + przepisy + słowa kluczowe → dopiero wtedy szukamy orzeczeń.

---

## 0) Jak przejść z ELI do zapytania (reguły uniwersalne)

1) Z aktu ELI zapisz:
   - `ELI/pageId` w formacie `DU/<rok>/<poz>` (np. `DU/2024/935`)
   - `title` (pełny tytuł ustawy/rozporządzenia)
   - 2–6 słów z `keywords` (jeśli są)
2) Zbuduj 2–3 frazy wyszukiwawcze:
   - **Fraza A (nazwa ustawy)**: krótka nazwa + “ustawa” (np. „Prawo o postępowaniu przed sądami administracyjnymi”)
   - **Fraza B (problem prawny)**: 1–2 pojęcia (np. „odrzucenie skargi”, „przedawnienie zobowiązania”)
   - **Fraza C (Dz.U.)**: `Dz.U. <rok> poz. <poz>` (jeśli wyszukiwarka wspiera)
3) Jeżeli w orzeczeniu pojawiają się podstawy prawne i cytaty Dz.U.:
   - zapisuj je jako **ELI-link** (normalizacja do `DU/<rok>/<poz>`) i wykorzystuj do kolejnych kwerend.

Minimalny output dla każdej znalezionej pozycji (do cytowania w odpowiedzi):
- `court_source`: `NSA` / `SN` / `TK` / `COMMON`
- `url` (bezpośredni link do orzeczenia)
- `case_number` / `sygnatura` (jeśli widoczna)
- `judgment_date` (jeśli widoczna)
- `legal_bases` / `referenced_regulations` (jeśli widoczne)

---

## 1) NSA / WSA — orzeczenia sądów administracyjnych

Wyszukiwarka (UI):  
- `https://orzeczenia.nsa.gov.pl/cbo/search`

Strona szczegółów (zwykle):  
- `https://orzeczenia.nsa.gov.pl/doc/<ID>`

Sugerowane filtry (kolejność):
1) **Sąd**: zacznij od „dowolny”, potem zawężaj:
   - „Naczelny Sąd Administracyjny” (NSA)
   - konkretne WSA (np. WSA w Warszawie)
2) **Fraza**: zacznij od Frazy A (nazwa ustawy), potem Fraza B.
3) **Data**: ustaw przedział tylko gdy wyników jest zbyt dużo.

Co zbierać (najważniejsze dla powiązania z ELI):
- podstawa prawna / powołane przepisy (często zawiera cytaty Dz.U. → da się mapować do ELI)
- sentencja + uzasadnienie (jeśli dostępne)

---

## 2) SN — Sąd Najwyższy

Wyszukiwarka (UI):  
- `https://www.sn.pl/wyszukiwanie/SitePages/orzeczenia.aspx`

Wskazówki praktyczne:
1) Zawężaj po **Izbie** (lista jest w UI, np. Cywilna/Karna/Pracy/itd.).
2) Jeżeli znasz typ sprawy:
   - cywilne: często frazy jak „odszkodowanie”, „naruszenie dóbr osobistych”, „umowa”
   - karne: „kara łączna”, „kasacja”, „rażące naruszenie”
3) Jeśli masz sygnaturę lub jej fragment — użyj jej jako frazy (najlepszy filtr).

Co zbierać:
- `sygnatura`
- data wydania
- link do uzasadnienia (PDF/HTML, zależnie od pozycji)
- podstawa prawna / powołane przepisy (jeśli widoczne)

---

## 3) TK — Trybunał Konstytucyjny

Portal / lista orzeczeń (UI):  
- `https://trybunal.gov.pl/orzeczenia`

IPO (wyszukiwarka):  
- `https://ipo.trybunal.gov.pl/ipo/Szukaj?cid=1`

Jak szukać:
1) Fraza A (nazwa ustawy) + Fraza B (problem) — TK często ma bardzo „tematyczne” opisy.
2) Zawężaj po dacie, jeśli wyników jest dużo.

Co zbierać:
- sygnatura TK
- sentencja
- uzasadnienie (link / pdf)
- przepisy (często konstytucyjne + ustawa oceniana)

---

## 4) Sądy powszechne (SR / SO / SA) — Portal Orzeczeń MS

Portal (UI):  
- `https://www.orzeczenia.ms.gov.pl/`

Uwaga: brak stabilnego publicznego API; traktuj jako „on-demand”.

Jak szukać:
1) Najpierw Fraza B (problem prawny) + 1–2 słowa z Frazy A (nazwa ustawy).
2) Zawężaj po:
   - rodzaju sądu / jednostce
   - dacie
   - hasłach tematycznych (jeśli UI je oferuje)

Co zbierać:
- sygnatura
- data
- sąd
- metryka (jeśli jest)
- powołane przepisy (często da się mapować do ELI, choć bywa mniej konsekwentne niż w NSA)

---

## 5) Szybka strategia “ELI → orzeczenia”

Jeżeli użytkownik pyta o akt ELI (np. `DU/2024/935`) i chcesz znaleźć orzeczenia:
1) Z `eli_acts`: weź `title` + `keywords`.
2) Najpierw **NSA/WSA** (najlepsze dopasowanie po podstawach prawnych i cytatach Dz.U.).
3) Potem **SN** (jeśli problem jest cywilny/karny/pracy).
4) Potem **sądy powszechne** (jeśli potrzebujesz praktyki SR/SO/SA).
5) **TK** tylko gdy sprawa ma wątek konstytucyjny lub akt był przedmiotem kontroli.

DoD (gotowe do użycia przez PrawoL):
- PrawoL potrafi wygenerować listę 5–20 linków do orzeczeń, z metryką i podstawą prawną,
- a każda podstawa prawna w Dz.U. jest możliwa do znormalizowania do ELI (`DU/<rok>/<poz>`) gdy dane wejściowe na to pozwalają.

