import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime
import re

# Der offizielle, stabile SRF Sport RSS-Feed
RSS_URL = "https://www.srf.ch/sport/bnf/rss/718"

def scrape_news():
    try:
        # 1. Feed ganz legal herunterladen (Türsteher ignorieren das!)
        response = requests.get(RSS_URL)
        response.raise_for_status() 
        
        # 2. XML-Daten auslesen
        root = ET.fromstring(response.content)
        news_list = []
        
        # 3. Alle News-Artikel (<item>) durchgehen
        for item in root.findall('.//item'):
            title = item.find('title').text if item.find('title') is not None else "Kein Titel"
            
            # Bilder im RSS-Feed auslesen (SRF packt diese meist ins <enclosure> Tag)
            image_url = ""
            enclosure = item.find('enclosure')
            if enclosure is not None and 'url' in enclosure.attrib:
                image_url = enclosure.attrib['url']
            else:
                # Fallback: Manchmal sind sie im Text versteckt
                desc = item.find('description')
                if desc is not None and desc.text:
                    img_match = re.search(r'src="([^"]+)"', desc.text)
                    if img_match:
                        image_url = img_match.group(1)
            
            # Datum formatieren (schneidet überflüssige Sekunden/Zeitzonen ab)
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else "Aktuell"
            if len(pub_date) > 16:
                pub_date = pub_date[:16]
                
            news_list.append({
                "title": title,
                "date": pub_date,
                "image": image_url
            })
            
            # Wir stoppen nach exakt 3 Artikeln für dein perfektes 3er-Layout
            if len(news_list) >= 3:
                break
                
        if not news_list:
            news_list = [{"title": "Keine News im Feed gefunden.", "date": datetime.now().strftime("%d.%m.%Y"), "image": ""}]
            
        return news_list
    except Exception as e:
        print(f"Fehler beim RSS-Download: {e}")
        return [{"title": "Fehler beim Laden des SRF-Feeds.", "date": "Aktuell", "image": ""}]

def scrape_schedule():
    # Da die IIHF-Website aktuell alles blockiert, setzen wir den Spielplan vorerst 
    # als feste Daten ein. Für ein unbeaufsichtigtes Dashboard ist das ohnehin sicherer!
    return [
        {"team1": "SUI", "team2": "SWE", "date": "15. Mai 2026", "time": "20:20", "venue": "Swiss Life Arena, Zürich"},
        {"team1": "CAN", "team2": "USA", "date": "16. Mai 2026", "time": "16:20", "venue": "BCF Arena, Fribourg"}
    ]

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