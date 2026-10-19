# BSIAW grupa 4

Projekt zespołowy na laboratorium **Bezpieczeństwo serwerów i aplikacji Web** (PWr, semestr zimowy 2026/27, grupa 2, środa).

Prosta aplikacja webowa z logowaniem (sesja), interakcją użytkowników (forum, chat lub komentarze) i bazą danych, którą w kolejnych laboratoriach wdrażamy w chmurze publicznej, zabezpieczamy i testujemy.

## Technologie

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black)

| Warstwa | Technologia |
|---|---|
| Backend | Python, Flask |
| Baza danych | PostgreSQL |
| Frontend | HTML, CSS, JavaScript |

## Aplikacja: Kinoteka

Serwis z recenzjami filmów. UI to celowo czysty HTML bez CSS i JS (wygląd nie wpływa na ocenę).

- rejestracja, logowanie, wylogowanie, profil użytkownika
- filmy: lista z wyszukiwarką, dodawanie z plakatem, usuwanie (autor lub admin)
- recenzje z oceną 1-10 (jedna na film na osobę), edycja przez autora
- komentarze pod recenzjami
- panel admina: blokowanie i odblokowywanie kont

### Struktura

```
app/
  __init__.py     fabryka aplikacji, obsługa błędów, komenda create-admin
  config.py       konfiguracja ze zmiennych środowiskowych
  models.py       User, Movie, Review, Comment
  auth.py         rejestracja, logowanie, profil
  movies.py       filmy, recenzje, komentarze, plakaty
  admin.py        panel admina
  main.py         /health dla load balancera
  security.py     log zdarzeń bezpieczeństwa, kontrola uprawnień
  storage.py      walidacja i zapis plakatów
  templates/      szablony HTML
migrations/       migracje bazy (Alembic)
```

## Uruchomienie lokalne (DEV)

Wymagania: Python 3.11+, Docker Desktop.

1. Sklonuj repo i utwórz środowisko:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Skopiuj `.env.example` do `.env` i ustaw `SECRET_KEY` (komenda do wygenerowania jest w pliku).

3. Uruchom bazę i utwórz tabele:

   ```bash
   docker compose up -d db
   flask db upgrade
   ```

4. Załóż konto admina (hasło poda się interaktywnie):

   ```bash
   flask create-admin admin admin@example.com
   ```

5. Start aplikacji:

   ```bash
   flask run
   ```

   Aplikacja: http://127.0.0.1:5000

Całość w kontenerach (aplikacja na gunicornie): `docker compose --profile app up --build`, adres http://127.0.0.1:8000.

Po zmianie modeli w `models.py`: `flask db migrate -m "opis zmiany"`, a potem `flask db upgrade`.

## Zabezpieczenia już w kodzie

| Zagrożenie | Zabezpieczenie |
|---|---|
| SQL injection | ORM SQLAlchemy, wszystkie zapytania parametryzowane |
| XSS | autoescape w Jinja, nowe linie zamieniane bezpiecznie (`nl2br`) |
| CSRF | token CSRF w każdym formularzu (Flask-WTF), akcje zmieniające dane tylko POST |
| Łamanie haseł | hashe scrypt (Werkzeug), limit 5 nieudanych logowań na minutę z IP |
| Enumeracja kont | ten sam komunikat i podobny czas odpowiedzi dla złego loginu i złego hasła |
| Przejęcie sesji | ciasteczko HttpOnly i SameSite=Lax, sesja 30 min, unieważnienie przy zmianie IP lub przeglądarki, czyszczenie sesji przy logowaniu |
| Złośliwy upload | weryfikacja zawartości przez Pillow, ponowne kodowanie obrazka, losowa nazwa pliku, limit 2 MB |
| IDOR | sprawdzanie właściciela przy edycji i usuwaniu, panel admina tylko dla roli admin |
| Open redirect | parametr `next` po logowaniu tylko na ścieżki w aplikacji |
| Brak śladów ataku | log zdarzeń `SECURITY` (logowania, blokady, odmowy dostępu, odrzucone pliki) |

Do zrobienia w L7: nagłówki bezpieczeństwa (CSP, HSTS, X-Frame-Options itd.), `SESSION_COOKIE_SECURE=true` za HTTPS, WAF.

## Uwagi do wdrożenia w chmurze (L3, L4)

- Za load balancerem ustaw `TRUSTED_PROXIES=1`, inaczej aplikacja zobaczy IP load balancera zamiast klienta (rate limit i ochrona sesji przestaną działać sensownie).
- Plakaty są na lokalnym dysku (`instance/uploads`). Przy kilku instancjach trzeba podmienić `LocalStorage` w `storage.py` na storage obiektowy (S3, GCS).
- Rate limit trzyma liczniki w pamięci procesu. Przy kilku instancjach ustaw `RATELIMIT_STORAGE_URI` na Redisa.
- Daty są zapisywane w UTC.

## Zakres prac

| Lab | Temat |
|---|---|
| L1 | Wybór aplikacji do implementacji |
| L2 | Implementacja podstawowej funkcjonalności (środowisko DEV) |
| L3 | Projekt architektury w chmurze (load balancer, skalowalna baza, domena, TLS poza serwerem aplikacji) |
| L4 | Implementacja architektury w chmurze publicznej |
| L5 | Proces CI/CD |
| L6 | Bezpieczeństwo w CI/CD (SAST, DAST, sekrety) |
| L7 | Zabezpieczenia w kodzie i konfiguracji (nagłówki, sesje, WAF, CDN, IDS/IPS) |
| L8 | Hardening infrastruktury (CIS, STIG, dobre praktyki, zalecenia producenta) |
| L9 | Testy bezpieczeństwa aplikacji i infrastruktury |
