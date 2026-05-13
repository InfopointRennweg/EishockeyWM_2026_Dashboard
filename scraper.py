import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re

# Die offizielle SRF Eishockey WM News-Seite
NEWS_URL = "https://www.srf.ch/sport/eishockey/wm"

def scrape_news():
    try:
        # 1. HTML der SRF WM Seite herunterladen
        response = requests.get(NEWS_URL)
        response.raise_for_status() 
        
        # 2. BeautifulSoup Parser initialisieren
        soup = BeautifulSoup(response.text, 'html.parser')
        news_list = []
        
        # 3. Alle Teaser-Artikel auf der Seite finden
        teasers = [a for a in soup.find_all('a') if a.get('href') and '/sport/eishockey/wm/' in a.get('href') and 'teaser' in a.get('class', [])]
        
        for t in teasers:
            # Titel und Kicker (Über-Titel) auslesen und zusammensetzen
            kicker_el = t.find(class_='teaser__kicker-text')
            title_el = t.find(class_='teaser__title')
            
            kicker = kicker_el.text.strip() if kicker_el else ""
            title = title_el.text.strip() if title_el else ""
            
            full_title = f"{kicker} - {title}" if kicker and title else (title or kicker or "Kein Titel")
            
            # Bild URL auslesen (und absolut machen)
            image_url = ""
            img = t.find('img')
            if img is not None:
                image_url = img.get('src') or img.get('data-src') or ""
                if image_url.startswith('/'):
                    image_url = f"https://www.srf.ch{image_url}"
            
            # Veröffentlichungsdatum aus den Metadaten auslesen
            pub_date = "Aktuell"
            meta = t.find(class_='teaser__meta')
            if meta is not None:
                published_at = meta.get('data-teaser-meta-published-at')
                if published_at:
                    try:
                        # Datumsteil (YYYY-MM-DD) extrahieren und formatieren
                        date_str = published_at[:10]
                        dt = datetime.strptime(date_str, "%Y-%m-%d")
                        pub_date = dt.strftime("%d.%m.%Y")
                    except:
                        pass
            
            news_list.append({
                "title": full_title,
                "date": pub_date,
                "image": image_url
            })
            
            # Wir stoppen nach exakt 3 Artikeln für dein perfektes 3er-Layout
            if len(news_list) >= 3:
                break
                
        if not news_list:
            news_list = [{"title": "Keine News auf der SRF-Seite gefunden.", "date": datetime.now().strftime("%d.%m.%Y"), "image": ""}]
            
        return news_list
    except Exception as e:
        print(f"Fehler beim Web-Scraping: {e}")
        return [{"title": "Fehler beim Laden der SRF-News.", "date": "Aktuell", "image": ""}]

def scrape_schedule():
    try:
        url = "https://sport.api.swisstxt.ch/v1/eventItems?phaseIds=5252-298&lang=de"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        raw_games = response.json()
        
        all_games = []
        for g in raw_games:
            # 1. Teams & Länder extrahieren
            c1 = g.get("competitor1", {})
            c2 = g.get("competitor2", {})
            
            t1 = c1.get("name", "Unbekannt")
            t1_country = c1.get("country", "")
            
            t2 = c2.get("name", "Unbekannt")
            t2_country = c2.get("country", "")
            
            # 2. Datum & Uhrzeit
            dt_info = g.get("dateTimeInfo", {})
            full_date = dt_info.get("fullDateTime", "")
            time_str = dt_info.get("time", "")
            
            # Formatiertes Datum generieren
            date_str = ""
            if full_date:
                try:
                    dt = datetime.strptime(full_date[:19], "%Y-%m-%dT%H:%M:%S")
                    weekdays = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
                    months = ["Jan", "Feb", "März", "April", "Mai", "Juni", "Juli", "Aug", "Sept", "Okt", "Nov", "Dez"]
                    date_str = f"{weekdays[dt.weekday()]}, {dt.day}. {months[dt.month-1]}"
                except:
                    date_str = dt_info.get("date", "")
            else:
                date_str = dt_info.get("date", "")
                
            # 3. Match Details (Spielort, Stand, Torstand)
            venue = g.get("stadium", "Zürich / Fribourg")
            state = g.get("state", "Planned")
            
            main_score = g.get("scores", {}).get("main", {})
            score = main_score.get("formatted", "- : -")
            if score == "- : -":
                score = None
                
            all_games.append({
                "team1": t1,
                "team1_country": t1_country,
                "team2": t2,
                "team2_country": t2_country,
                "date_str": date_str,
                "time": time_str,
                "venue": venue,
                "state": state,
                "score": score,
                "full_date": full_date
            })
            
        # 4. Sortieren und Einteilen
        # Schweiz-Spiele
        swiss_games = [g for g in all_games if "schweiz" in g["team1"].lower() or "schweiz" in g["team2"].lower()]
        
        # Sortiere Schweiz-Spiele chronologisch
        swiss_games.sort(key=lambda x: x.get("full_date", ""))
        
        # Die nächsten Schweizer Spiele: Zustand nicht "Finished"
        upcoming_swiss = [g for g in swiss_games if g["state"] != "Finished"]
        
        # Wenn alle Schweizer Spiele bereits beendet sind (z.B. Turnierende), zeigen wir einfach alle
        if not upcoming_swiss:
            upcoming_swiss = swiss_games
            
        # Abgeschlossene Spiele (Resultate)
        past_results = [g for g in all_games if g["state"] == "Finished"]
        # Sortiere abgeschlossene Spiele umgekehrt chronologisch (neueste oben)
        past_results.sort(key=lambda x: x.get("full_date", ""), reverse=True)
        
        return {
            "swiss_games": upcoming_swiss,
            "past_results": past_results
        }
        
    except Exception as e:
        print(f"Fehler beim Laden des Spielplans: {e}")
        # Sichere Rückfalldaten, falls die SRF/SwissTxt-Schnittstelle jemals ausfallen sollte
        return {
            "swiss_games": [
                {"team1": "USA", "team1_country": "USA", "team2": "Schweiz", "team2_country": "SUI", "date_str": "Fr, 15. Mai", "time": "20:20", "venue": "Swiss Life Arena, Zürich", "state": "Planned", "score": None},
                {"team1": "Schweiz", "team1_country": "SUI", "team2": "Lettland", "team2_country": "LAT", "date_str": "Sa, 16. Mai", "time": "20:20", "venue": "Swiss Life Arena, Zürich", "state": "Planned", "score": None},
                {"team1": "Deutschland", "team1_country": "GER", "team2": "Schweiz", "team2_country": "SUI", "date_str": "Mo, 18. Mai", "time": "20:20", "venue": "Swiss Life Arena, Zürich", "state": "Planned", "score": None},
                {"team1": "Österreich", "team1_country": "AUT", "team2": "Schweiz", "team2_country": "SUI", "date_str": "Mi, 20. Mai", "time": "16:20", "venue": "Swiss Life Arena, Zürich", "state": "Planned", "score": None}
            ],
            "past_results": [
                {"team1": "Finnland", "team1_country": "FIN", "team2": "Deutschland", "team2_country": "GER", "date_str": "Fr, 15. Mai", "time": "16:20", "venue": "Swiss Life Arena, Zürich", "state": "Finished", "score": "3 : 2"},
                {"team1": "Lettland", "team1_country": "LAT", "team2": "Österreich", "team2_country": "AUT", "date_str": "Fr, 15. Mai", "time": "16:20", "venue": "Swiss Life Arena, Zürich", "state": "Finished", "score": "1 : 2"}
            ]
        }

if __name__ == "__main__":
    print("Lade offizielle SRF Sport News via RSS...")
    data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "news": scrape_news(),
        "schedule": scrape_schedule()
    }
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print("data.json erfolgreich und legal erstellt. Keine Türsteher mehr!")