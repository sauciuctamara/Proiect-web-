import streamlit as st
import mysql.connector
import json

# Setari generale pagina
st.set_page_config(page_title="Repertoriu Teatrul ACT", layout="wide", page_icon="🎭")

# Conexiune la MySQL pastrata in cache
@st.cache_resource
def init_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="crawler_teatru"
    )

conn = init_connection()

# Ruleaza interogari SELECT si intoarce randurile ca dictionare
def extrage_date(query, params=None):
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params or ())
    return cursor.fetchall()

# Citire parametri din URL pentru navigare si filtrare
query_params = st.query_params
id_spectacol = query_params.get("id")
pagina_curenta = query_params.get("page", "shows")
termen_cautare = query_params.get("search", "")

# Pagina program reprezentatii
if pagina_curenta == "schedule":
    st.title("📅 Program Reprezentatii")
    
    if st.button("⬅ Inapoi la lista de spectacole"):
        st.query_params.clear()
        st.rerun()
        
    st.divider()
    
    sql_program = """
        SELECT r.data_ora, r.locatie, s.titlu 
        FROM reprezentatii r
        JOIN spectacole s ON r.id_spectacol = s.id
        ORDER BY r.data_ora ASC
    """
    programari = extrage_date(sql_program)
    
    if programari:
        for p in programari:
            p['Data si Ora'] = p.pop('data_ora').strftime("%d-%m-%Y %H:%M")
            p['Spectacol'] = p.pop('titlu')
            p['Locatie'] = p.pop('locatie')
        st.dataframe(programari, use_container_width=True, hide_index=True)
    else:
        st.info("In acest moment nu exista reprezentatii programate in sistem.")

# Pagina detalii spectacol
elif id_spectacol:
    if st.button("⬅ Inapoi la lista"):
        st.query_params.clear()
        st.rerun()
        
    spectacol = extrage_date("SELECT * FROM spectacole WHERE id = %s", (id_spectacol,))
    
    if spectacol:
        s = spectacol[0]
        st.title(s['titlu'])
        
        col1, col2 = st.columns([1, 2.5])
        
        with col1:
            if s.get('cale_afis'):
                try:
                    st.image(s['cale_afis'], use_container_width=True)
                except Exception:
                    st.info("Eroare la incarcarea afisului")
            else:
                st.info("Fara afis")
                
        with col2:
            st.markdown("### Informatii Generale")
            if s.get('autor'): st.write(f"**Autor:** {s['autor']}")
            if s.get('regizor'): st.write(f"**Regizor:** {s['regizor']}")
            if s.get('durata_text'): st.write(f"**Durata:** {s['durata_text']}")
            if s.get('varsta_recomandata'): st.write(f"**Recomandare varsta:** {s['varsta_recomandata']}")
            
            st.markdown("### Descriere")
            st.write(s['descriere'] if s['descriere'] else "Nu exista descriere publica pentru acest spectacol.")
            
        st.divider()
        
        # Preluare distributie si echipa din JSON
        col_distrib, col_echipa = st.columns(2)
        with col_distrib:
            st.subheader("🎭 Distributie")
            actori = json.loads(s['distributie_json']) if s['distributie_json'] else []
            if actori:
                for actor in actori:
                    nume = actor.get('name', '')
                    rol = actor.get('character', '')
                    if rol:
                        st.markdown(f"- **{nume}** ({rol})")
                    else:
                        st.markdown(f"- {nume}")
            else:
                st.write("Distributia nu a fost publicata.")
                
        with col_echipa:
            st.subheader("🎬 Echipa Artistica")
            echipa = json.loads(s['echipa_json']) if s['echipa_json'] else []
            if echipa:
                for membru in echipa:
                    rol = membru.get('role', 'Membru')
                    nume = membru.get('name', '')
                    st.markdown(f"- **{rol}:** {nume}")
            else:
                st.write("Echipa nu a fost publicata.")

        # Reprezentatii pentru spectacolul selectat
        st.divider()
        st.subheader("📅 Urmatoarele Reprezentatii")
        
        sql_rep_spectacol = """
            SELECT data_ora, locatie, url_sursa 
            FROM reprezentatii 
            WHERE id_spectacol = %s 
            ORDER BY data_ora ASC
        """
        reprezentatii = extrage_date(sql_rep_spectacol, (id_spectacol,))
        
        if reprezentatii:
            for rep in reprezentatii:
                data_formatata = rep['data_ora'].strftime("%d-%m-%Y ora %H:%M")
                locatie = rep['locatie']
                url_bilet = rep['url_sursa']
                
                with st.container(border=True):
                    col_data, col_bilet = st.columns([3, 1], vertical_alignment="center")
                    with col_data:
                        st.markdown(f"**{data_formatata}** — {locatie}")
                    with col_bilet:
                        if url_bilet:
                            st.link_button("🎟️ Cumpara Bilet", url_bilet, use_container_width=True)
                        else:
                            st.button("Bilete indisponibile", disabled=True, use_container_width=True)
        else:
            st.info("Nu exista reprezentatii programate in viitorul apropiat pentru acest spectacol.")

# Pagina principala cu lista de spectacole
else:
    st.title("🎭 Repertoriu Teatrul ACT")
    
    col_btn, col_search = st.columns([1, 2], vertical_alignment="bottom")
    
    with col_btn:
        if st.button("📅 Vezi Programul (Calendar)", use_container_width=True):
            st.query_params["page"] = "schedule"
            st.rerun()
            
    with col_search:
        # Sincronizare cautare cu parametrul search din URL
        input_cautare = st.text_input(
            "Cauta", 
            value=termen_cautare, 
            placeholder="🔍 Cauta un spectacol (dupa titlu)...", 
            label_visibility="collapsed"
        )
        if input_cautare != termen_cautare:
            if input_cautare:
                st.query_params["search"] = input_cautare
            else:
                if "search" in st.query_params:
                    del st.query_params["search"]
            st.rerun()

    st.divider()
    
    if termen_cautare:
        spectacole = extrage_date(
            "SELECT id, titlu, autor, regizor, cale_afis FROM spectacole WHERE titlu LIKE %s", 
            (f"%{termen_cautare}%",)
        )
    else:
        spectacole = extrage_date("SELECT id, titlu, autor, regizor, cale_afis FROM spectacole")

    if not spectacole:
        st.warning("Nu am gasit niciun spectacol conform cautarii tale.")
    else:
        # Afisare in grila de 4 coloane 
        coloane_pe_rand = 4 
        randuri = [spectacole[i:i + coloane_pe_rand] for i in range(0, len(spectacole), coloane_pe_rand)]
        
        for rand in randuri:
            coloane = st.columns(coloane_pe_rand) 
            
            for idx, spec in enumerate(rand):
                with coloane[idx]:
                    with st.container(border=True):
                        
                        st.markdown(f"<h4 style='min-height: 60px; margin-bottom: 10px; font-size: 1.1rem;'>{spec['titlu']}</h4>", unsafe_allow_html=True)
                        
                        if spec.get('cale_afis'):
                            try:
                                st.image(spec['cale_afis'], use_container_width=True)
                            except Exception:
                                st.info("Eroare incarcare afis")
                        else:
                            st.info("Fara afis")
                        
                        autor_text = spec['autor'] if spec.get('autor') else "-"
                        regizor_text = spec['regizor'] if spec.get('regizor') else "-"
                        
                        st.markdown(f"""
                            <div style='min-height: 50px; font-size: 0.9rem; opacity: 0.8; margin-top: 15px; margin-bottom: 15px;'>
                                <b>Autor:</b> {autor_text}<br>
                                <b>Regizor:</b> {regizor_text}
                            </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button("Vezi Detalii", key=f"btn_{spec['id']}", use_container_width=True):
                            st.query_params["id"] = spec['id']
                            st.rerun()