import streamlit as st
from pathlib import Path
import re
import pandas as pd
import pdfplumber
import tempfile

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# --- REPORTLAB PDF GENERATOR ---
def genereer_pdf(df, serie_kolommen, klasse_naam, evenement_naam, output_pdf_pad):
    doc = SimpleDocTemplate(
        str(output_pdf_pad),
        pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20
    )
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('MainTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#004080'), spaceAfter=2)
    sub_style = ParagraphStyle('SubTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#333333'), spaceAfter=2)
    event_style = ParagraphStyle('EventInfo', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#d9534f'), spaceAfter=10)
    
    cell_style = ParagraphStyle('Cell', fontName='Helvetica', fontSize=8, alignment=1)
    cell_left = ParagraphStyle('CellLeft', fontName='Helvetica', fontSize=8, alignment=0)
    cell_bold = ParagraphStyle('CellBold', fontName='Helvetica-Bold', fontSize=8, alignment=1)
    cutoff_style = ParagraphStyle('CutoffText', fontName='Helvetica-Bold', fontSize=8, alignment=1, textColor=colors.HexColor('#d9534f'))

    elements.append(Paragraph("EUROL NEDERLANDS KAMPIOENSCHAP AUTOCROSS", title_style))
    elements.append(Paragraph(str(evenement_naam), event_style))
    elements.append(Paragraph(str(klasse_naam), sub_style))
    elements.append(Paragraph("Tussenstand / Eindklassement na manches", sub_style))
    elements.append(Spacer(1, 10))

    headers = ['Pos', 'Nr.', 'Naam', 'Totaal'] + serie_kolommen
    table_data = [[Paragraph(f"<b>{h}</b>", cell_bold) for h in headers]]

    for idx, row in df.iterrows():
        if row['Pos'] == 16:
            cutoff_row = [Paragraph("<b>--- GEEN FINALE ---</b>", cutoff_style)] + [""] * (len(headers) - 1)
            table_data.append(cutoff_row)

        r_data = [
            Paragraph(f"<b>{row['Pos']}</b>", cell_bold),
            Paragraph(str(row['Startnr']), cell_style),
            Paragraph(str(row['Naam']), cell_left),
            Paragraph(f"<b>{row['Totaal punten']}</b>", cell_bold)
        ]
        for s in serie_kolommen:
            val = str(row[s]) if pd.notna(row[s]) and str(row[s]) != "" else ""
            r_data.append(Paragraph(val, cell_style))
        table_data.append(r_data)

    col_widths = [30, 35, 160, 45] + [35] * len(serie_kolommen)
    t = Table(table_data, colWidths=col_widths)
    
    t_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#004080')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fbfd')])
    ]

    if len(df) >= 16:
        cutoff_idx = 16
        t_style.append(('SPAN', (0, cutoff_idx), (-1, cutoff_idx)))
        t_style.append(('BACKGROUND', (0, cutoff_idx), (-1, cutoff_idx), colors.HexColor('#fdf2f2')))
        t_style.append(('LINEABOVE', (0, cutoff_idx), (-1, cutoff_idx), 1.0, colors.HexColor('#d9534f')))
        t_style.append(('LINEBELOW', (0, cutoff_idx), (-1, cutoff_idx), 1.0, colors.HexColor('#d9534f')))

    t.setStyle(TableStyle(t_style))
    elements.append(t)
    doc.build(elements)

# --- VERWERK LOGICA ---
def verwerk_files(uploaded_files, temp_dir):
    rijders = []
    klasse_naam = "Autocross Klasse"
    evenement_naam = "NK Autocross"

    file_paths = []
    for u_file in uploaded_files:
        p = Path(temp_dir) / u_file.name
        with open(p, "wb") as f:
            f.write(u_file.getbuffer())
        file_paths.append(p)

    verzamel_pdf = next((p for p in file_paths if "na" in p.name.lower() or "uitslag" in p.name.lower()), None)

    if verzamel_pdf:
        with pdfplumber.open(verzamel_pdf) as pdf:
            tekst = pdf.pages[0].extract_text() or ""
            for regel in tekst.split('\n'):
                if "NK Autocross" in regel or "Eurol NK" in regel:
                    evenement_naam = regel.strip()
                if re.search(r'A\d+\s*-\s*', regel) or "klasse" in regel.lower():
                    klasse_naam = regel.split("Lochem")[0].strip()

            serie_kolommen = ["A6", "R2.", "R3.", "R4.", "R5.", "R6."]
            for regel in tekst.split('\n'):
                if "Niet geclassificeerd" in regel or "Pos" in regel or "Naam" in regel:
                    continue
                m_nr = re.search(r'^\s*(\d+)\s*\|\s*(\d{3})\s+([A-Za-z\s/*]+?)\s*\|\s*(\d+)', regel)
                m_naam = re.search(r'^\s*(\d+)\s*\|\s*([A-Za-z\s/*]+?)\s+(\d{3})\s*\|\s*(\d+)', regel)
                
                if m_nr:
                    pos, nr, naam, totaal = m_nr.groups()
                    rijders.append({"Pos": int(pos), "Startnr": nr, "Naam": naam.strip(), "Totaal punten": int(totaal)})
                elif m_naam:
                    pos, naam, nr, totaal = m_naam.groups()
                    rijders.append({"Pos": int(pos), "Startnr": nr, "Naam": naam.strip(), "Totaal punten": int(totaal)})

        df = pd.DataFrame(rijders).sort_values(by="Pos", ascending=True)
        for col in serie_kolommen:
            if col not in df.columns: df[col] = ""
    else:
        rijders_dict, alle_series = {}, set()
        p1 = re.compile(r'^\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(\d+)\b')
        p2 = re.compile(r'^\s*(\d+)\s+(\d+)\s+(.+?)\s+(\d+)\b')

        for pdf_pad in file_paths:
            with pdfplumber.open(pdf_pad) as pdf:
                tekst = pdf.pages[0].extract_text() or ""
                for regel in tekst.split('\n'):
                    if "NK Autocross" in regel or "Eurol NK" in regel:
                        evenement_naam = regel.strip()
                    if re.search(r'A\d+\s*-\s*', regel) or "klasse" in regel.lower():
                        klasse_naam = regel.split("Lochem")[0].strip()

                s_match = re.search(r'(\d+e [Mm]anche\s*-\s*Serie \d+|\bSerie \d+\b)', tekst)
                serie_naam = s_match.group(1).strip() if s_match else pdf_pad.stem
                alle_series.add(serie_naam)

                for regel in tekst.split('\n'):
                    if "Pos" in regel and "Naam" in regel: continue
                    match = p1.match(regel.strip()) or p2.match(regel.strip())
                    if match:
                        pos, nr, naam, punten = match.groups()
                        if nr not in rijders_dict:
                            rijders_dict[nr] = {"Startnr": nr, "Naam": naam.strip(), "Punten": {}}
                        rijders_dict[nr]["Punten"][serie_naam] = int(punten)

        serie_kolommen = sorted(list(alle_series))
        tabel_data = []
        for nr, info in rijders_dict.items():
            r_entry = {"Startnr": info["Startnr"], "Naam": info["Naam"]}
            tot = sum(pts for pts in info["Punten"].values() if isinstance(pts, int))
            r_entry["Totaal punten"] = tot
            for s in serie_kolommen: r_entry[s] = info["Punten"].get(s, "")
            tabel_data.append(r_entry)

        df = pd.DataFrame(tabel_data)
        df['Max_Score'] = df[serie_kolommen].apply(lambda r: max([v for v in r if isinstance(v, int)] + [0]), axis=1)
        df = df.sort_values(by=["Totaal punten", "Max_Score"], ascending=[False, False]).drop(columns=['Max_Score'])
        df.insert(0, 'Pos', range(1, 1 + len(df)))

    schone_klasse = re.sub(r'^[A-Za-z0-9]+\s*-\s*', '', klasse_naam)
    schone_klasse = re.sub(r'[^a-zA-Z0-9_-]', '_', schone_klasse).strip('_')
    out_pdf = Path(temp_dir) / f"Finale_{schone_klasse}.pdf"

    genereer_pdf(df, serie_kolommen, klasse_naam, evenement_naam, out_pdf)
    return out_pdf, df

# --- STREAMLIT MOBIELE INTERFACE ---
st.set_page_config(page_title="NK Autocross Finale Generator", layout="centered")

st.title("🏆 NK Autocross Generator")
st.write("Upload de PDF's en genereer direct het finale-klassement.")

uploaded_files = st.file_uploader("Selecteer manche PDF(s)", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 Genereer Klassements PDF", use_container_width=True):
        with st.spinner("Bezig met verwerken..."):
            with tempfile.TemporaryDirectory() as temp_dir:
                pdf_path, df = verwerk_files(uploaded_files, temp_dir)
                
                with open(pdf_path, "rb") as f:
                    pdf_data = f.read()

                st.success("Klaar!")
                
                st.download_button(
                    label="📥 Download Finale PDF",
                    data=pdf_data,
                    file_name=pdf_path.name,
                    mime="application/pdf",
                    use_container_width=True
                )
                
                st.write("---")
                st.subheader("Voorbeeld Tussenstand")
                st.dataframe(df, use_container_width=True)