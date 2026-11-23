import httpx
from bs4 import BeautifulSoup
from protego import Protego
import mysql.connector
import json
import os
import hashlib
import re
import time
from datetime import datetime

# Configurare conexiune MySQL (parola goala pentru XAMPP)
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "crawler_teatru"
}

url_baza = "https://www.teatrulact.ro"
url_ajax = f"{url_baza}/wp-admin/admin-ajax.php"
folder_afise = "static/posters"
os.makedirs(folder_afise, exist_ok=True)

nume_robot = "TeatrulACT-Crawler/1.0"
headere_cereri = {
    "User-Agent": f"{nume_robot} (Proiect Universitar Tehnologii Web)"
}


def verifica_robots_txt(client, url_tinta):
    """Citeste si interpreteaza robots.txt folosind Protego."""
    try:
        rasp = client.get(f"{url_baza}/robots.txt", timeout=10.0)
        if rasp.status_code == 200:
            rp = Protego.parse(rasp.text)
            permis = rp.can_fetch(url_tinta, nume_robot)
            delay = rp.crawl_delay(nume_robot)
            return permis, (delay if delay else 2.0)
    except Exception as e:
        print(f"[!] Nu s-a putut citi robots.txt ({e}), continuam cu pauza de siguranta.")
    return True, 2.0


def descarca_afis(client, url_imagine):
    """Descarca afisul si il salveaza local identificat prin hash SHA-256."""
    if not url_imagine:
        return None, None
    try:
        url_imagine = url_imagine.strip()
        if url_imagine.startswith("//"):
            url_imagine = "https:" + url_imagine
        elif not url_imagine.startswith("http"):
            url_imagine = url_baza + url_imagine

        raspuns = client.get(url_imagine, timeout=15.0)
        raspuns.raise_for_status()

        date_imagine = raspuns.content
        hash_imagine = hashlib.sha256(date_imagine).hexdigest()
        cale_fisier = os.path.join(folder_afise, f"{hash_imagine}.jpg")

        if not os.path.exists(cale_fisier):
            with open(cale_fisier, "wb") as f:
                f.write(date_imagine)
        return cale_fisier, hash_imagine
    except Exception as e:
        print(f"[-] Eroare descarcare afis: {e}")
        return None, None


def extrage_reprezentatii_ajax(client, post_id, all_tickets="1"):
    """Apeleaza endpoint-ul AJAX al temei WordPress pentru a obtine programul real."""
    if not post_id:
        return []

    luni_ro = {
        "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
        "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
        "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12
    }

    payload = {
        "action": "event-filter",
        "date": "",
        "post_id": post_id,
        "all_tickets": all_tickets
    }

    reprezentatii_gasite = []
    try:
        rasp = client.post(url_ajax, data=payload, timeout=15.0)
        rasp.raise_for_status()
        soup_prog = BeautifulSoup(rasp.text, "html.parser")

        for li in soup_prog.find_all("li"):
            div_timp = li.find("div", class_="time")
            if not div_timp:
                continue

            text_timp = div_timp.get_text(strip=True).lower()
            # Formatul de pe site: "19:30, 23 noiembrie 2026"
            match = re.search(
                r'(\d{1,2}):(\d{2})\s*,?\s*(\d{1,2})\s+([a-zăâîșț]+)\s*(\d{4})?',
                text_timp
            )
            if not match:
                continue

            ora = int(match.group(1))
            minut = int(match.group(2))
            zi = int(match.group(3))
            luna_text = match.group(4)
            an_text = match.group(5)

            luna_numar = luni_ro.get(luna_text)
            if not luna_numar:
                continue

            if an_text:
                an = int(an_text)
            else:
                an = datetime.now().year
                if datetime.now().month >= 9 and luna_numar < 9:
                    an += 1

            data_finala = datetime(an, luna_numar, zi, ora, minut)

            # Extragere link bilet
            div_ticket = li.find("div", class_="ticket")
            link_bilet = div_ticket.find("a", href=True) if div_ticket else None
            url_bilet = link_bilet["href"].strip() if link_bilet else None

            # Extragere locatie
            locatie = "Teatrul ACT"
            div_loc = li.find("div", class_="event_auditory")
            if div_loc:
                text_loc = re.sub(r'^Locatia:\s*', '', div_loc.get_text(strip=True), flags=re.I)
                text_loc = text_loc.rstrip(", ").strip()
                if text_loc:
                    locatie = text_loc

            reprezentatii_gasite.append({
                "data_ora": data_finala,
                "locatie": locatie,
                "url_bilet": url_bilet
            })
    except Exception as e:
        print(f"    [!] Eroare la preluarea programului AJAX (post_id={post_id}): {e}")

    return reprezentatii_gasite


def porneste_crawler():
    print("[*] Conectare la baza de date...")
    db = mysql.connector.connect(**db_config)
    cursor = db.cursor(dictionary=True)

    with httpx.Client(headers=headere_cereri, follow_redirects=True, timeout=20.0) as client:
        try:
            url_spectacole = f"{url_baza}/event_categories/spectacole/"
            permis, pauza_cereri = verifica_robots_txt(client, url_spectacole)
            if not permis:
                print("[-] Accesul este interzis de robots.txt. Oprim executia.")
                return

            print(f"[*] robots.txt verificat. Pauza intre cereri: {pauza_cereri}s")
            print(f"[*] Accesez lista de spectacole: {url_spectacole}")

            rasp_lista = client.get(url_spectacole)
            rasp_lista.raise_for_status()
            soup_lista = BeautifulSoup(rasp_lista.text, "html.parser")

            linkuri_unice = []
            for tag in soup_lista.find_all("a", href=True):
                href = tag.get("href")
                if "/movies/" in href and href not in linkuri_unice:
                    linkuri_unice.append(href)

            print(f"[*] Am gasit {len(linkuri_unice)} spectacole. Incepem extragerea...\n")

            for link in linkuri_unice:
                time.sleep(pauza_cereri)

                url_spectacol = link if link.startswith("http") else f"{url_baza}{link}"
                print(f"[*] Procesez: {url_spectacol}")

                try:
                    rasp_spectacol = client.get(url_spectacol)
                    rasp_spectacol.raise_for_status()
                    soup_spectacol = BeautifulSoup(rasp_spectacol.text, "html.parser")

                    # Titlu
                    div_titlu = soup_spectacol.find("div", class_="page_title event") or soup_spectacol.find("h1")
                    titlu = div_titlu.get_text(strip=True) if div_titlu else "Titlu necunoscut"

                    # Autor (curatat sigur doar la inceputul sirului)
                    div_autor = soup_spectacol.find("div", class_="event_country")
                    autor = re.sub(r'^de\s+', '', div_autor.get_text(strip=True), flags=re.I) if div_autor else None

                    # Regizor
                    div_regizor = soup_spectacol.find("div", class_="event_director")
                    regizor = div_regizor.get_text(strip=True) if div_regizor else None

                    # Varsta recomandata
                    div_varsta = soup_spectacol.find("div", class_="event_restriction")
                    varsta = div_varsta.get_text(strip=True) if div_varsta else None

                    # Durata
                    durata_text = None
                    durata_minute = None
                    div_durata = soup_spectacol.find("div", class_="movies_length")
                    if div_durata:
                        text_brut_durata = div_durata.get_text(strip=True)
                        match_durata = re.search(r'(\d+)\s*h\s*(\d+)?\s*min', text_brut_durata)
                        if match_durata:
                            ore = int(match_durata.group(1))
                            minute = int(match_durata.group(2)) if match_durata.group(2) else 0
                            durata_minute = ore * 60 + minute
                            durata_text = f"{ore}h {minute}min"
                        else:
                            match_min = re.search(r'(\d+)\s*min', text_brut_durata)
                            if match_min:
                                durata_minute = int(match_min.group(1))
                                durata_text = f"{durata_minute} min"

                    # Distributie JSON
                    distributie = []
                    div_actori = soup_spectacol.find("div", class_="event_actors")
                    if div_actori:
                        for actor in div_actori.get_text(strip=True).split(','):
                            if not actor.strip():
                                continue
                            if '-' in actor:
                                parti = actor.split('-', 1)
                                distributie.append({"name": parti[0].strip(), "character": parti[1].strip()})
                            else:
                                distributie.append({"name": actor.strip()})
                    cast_json = json.dumps(distributie, ensure_ascii=False) if distributie else None

                    # Echipa artistica JSON
                    echipa = []
                    div_echipa = soup_spectacol.find("div", class_="event_official_sites")
                    if div_echipa:
                        for membru in div_echipa.get_text(strip=True).split(','):
                            if not membru.strip():
                                continue
                            if ':' in membru:
                                parti = membru.split(':', 1)
                                echipa.append({"role": parti[0].strip(), "name": parti[1].strip()})
                            else:
                                echipa.append({"name": membru.strip()})
                    team_json = json.dumps(echipa, ensure_ascii=False) if echipa else None

                    # Descriere
                    descriere = ""
                    h1_prez = soup_spectacol.find("h1", string=re.compile("Prezentare spectacol", re.I))
                    if h1_prez:
                        paragrafe = []
                        frate = h1_prez.find_next_sibling()
                        while frate and frate.name == "p":
                            paragrafe.append(frate.get_text(strip=True))
                            frate = frate.find_next_sibling()
                        descriere = "\n".join(paragrafe)

                    # Descarcare afis
                    img_afis = soup_spectacol.find("img", class_="open_entry_image")
                    url_imagine = img_afis["src"] if img_afis and img_afis.has_attr("src") else None
                    cale_afis, hash_afis = descarca_afis(client, url_imagine)

                    # Salvare/actualizare spectacol
                    sql_insert_show = """
                        INSERT INTO spectacole 
                        (titlu, autor, regizor, descriere, durata_minute, durata_text, varsta_recomandata, 
                         distributie_json, echipa_json, stocare_afis, cale_afis, url_sursa_afis, hash_afis, 
                         url_sursa, ultima_verificare)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'file', %s, %s, %s, %s, NOW())
                        ON DUPLICATE KEY UPDATE 
                            titlu=VALUES(titlu),
                            autor=VALUES(autor),
                            regizor=VALUES(regizor),
                            descriere=VALUES(descriere),
                            durata_minute=VALUES(durata_minute),
                            durata_text=VALUES(durata_text),
                            varsta_recomandata=VALUES(varsta_recomandata),
                            distributie_json=VALUES(distributie_json),
                            echipa_json=VALUES(echipa_json),
                            cale_afis=VALUES(cale_afis),
                            url_sursa_afis=VALUES(url_sursa_afis),
                            hash_afis=VALUES(hash_afis),
                            ultima_verificare=NOW()
                    """
                    cursor.execute(sql_insert_show, (
                        titlu, autor, regizor, descriere, durata_minute, durata_text, varsta,
                        cast_json, team_json, cale_afis, url_imagine, hash_afis, url_spectacol
                    ))
                    db.commit()

                    cursor.execute("SELECT id FROM spectacole WHERE url_sursa = %s", (url_spectacol,))
                    rezultat_id = cursor.fetchone()
                    id_spectacol = rezultat_id["id"] if rezultat_id else None

                    print(f"    -> Salvat spectacol: {titlu}")

                    # Extragere program reprezentatii prin AJAX
                    if id_spectacol:
                        input_post_id = soup_spectacol.find("input", id="post_id")
                        input_all_tickets = soup_spectacol.find("input", id="show_all_tickets")

                        post_id = input_post_id["value"] if input_post_id and input_post_id.has_attr("value") else None
                        all_tickets = input_all_tickets["value"] if input_all_tickets and input_all_tickets.has_attr("value") else "1"

                        time.sleep(0.5)
                        reprezentatii = extrage_reprezentatii_ajax(client, post_id, all_tickets)

                        for rep in reprezentatii:
                            sql_insert_perf = """
                                INSERT INTO reprezentatii 
                                (id_spectacol, data_ora, locatie, url_sursa, ultima_verificare)
                                VALUES (%s, %s, %s, %s, NOW())
                                ON DUPLICATE KEY UPDATE 
                                    locatie=VALUES(locatie),
                                    url_sursa=VALUES(url_sursa),
                                    ultima_verificare=NOW()
                            """
                            cursor.execute(sql_insert_perf, (
                                id_spectacol, rep["data_ora"], rep["locatie"], rep["url_bilet"]
                            ))
                        db.commit()

                        if reprezentatii:
                            print(f"    -> Salvat {len(reprezentatii)} reprezentatii in program")

                except Exception as e:
                    print(f"[-] Eroare la spectacolul {url_spectacol}: {e}")

        finally:
            if cursor:
                cursor.close()
            if db.is_connected():
                db.close()
                print("\n[*] Conexiunea la baza de date a fost inchisa in siguranta.")


if __name__ == "__main__":
    porneste_crawler()