import streamlit as st
import os
from datetime import datetime
from ALEXA1.ALEXA1.joelma import AssistentePDF
import pdfplumber
import re
import shutil

# Inicializa assistente
assistente = AssistentePDF()

st.set_page_config(page_title="Assistente PDF", layout="wide")
st.title("📄 Assistente PDF")

# --- Sidebar: Modos ---
st.sidebar.header("Modos de Interação")
modo_digitacao = st.sidebar.checkbox("Modo Digitação (sem voz)", value=assistente.modo_digitacao)
modo_silencioso = st.sidebar.checkbox("Modo Silencioso", value=assistente.modo_silencioso)

assistente.modo_digitacao = modo_digitacao
assistente.modo_silencioso = modo_silencioso

st.sidebar.write(f"Modo interação: {'Digitação' if modo_digitacao else 'Voz'}")
st.sidebar.write(f"Modo silencioso: {'Ativado' if modo_silencioso else 'Desativado'}")

# --- Seção PDFs ---
st.header("📂 Gerenciamento de PDFs")

pdfs_disponiveis = [f for f in os.listdir(assistente.PDF_FOLDER) if f.lower().endswith(".pdf")]
st.subheader("PDFs Disponíveis")
if pdfs_disponiveis:
    st.write(pdfs_disponiveis)
else:
    st.write("Nenhum PDF disponível")

# Baixar PDF
st.subheader("Baixar PDF")
pdf_baixar = st.text_input("Nome do PDF para baixar")
if st.button("Baixar PDF"):
    if pdf_baixar.strip():
        assistente.baixar_pdf(pdf_baixar)
        st.success(f"PDF '{pdf_baixar}' processado")
    else:
        st.warning("Informe o nome do PDF")

# Buscar termo
st.subheader("Buscar Termo em PDFs")
termo_busca = st.text_input("Termo para buscar")
if st.button("Buscar Termo"):
    resultados = []
    termo_regex = re.compile(r'\S*' + re.escape(termo_busca) + r'\S*', re.IGNORECASE)
    for pdf_name in pdfs_disponiveis:
        pdf_path = os.path.join(assistente.PDF_FOLDER, pdf_name)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    matches = termo_regex.findall(text)
                    if matches:
                        resultados.append(f"{pdf_name} página {i+1}: {matches[:5]}")
        except:
            resultados.append(f"Erro ao processar {pdf_name}")
    if resultados:
        st.write(resultados)
    else:
        st.write(f"Nenhum resultado encontrado para '{termo_busca}'")

# --- Seção Agenda ---
st.header("📅 Agenda de Compromissos")

# Listar compromissos
st.subheader("Compromissos")
assistente.cursor.execute("SELECT id, titulo, data_hora FROM compromissos ORDER BY data_hora")
rows = assistente.cursor.fetchall()
if rows:
    for r in rows:
        st.write(f"ID {r[0]} - {r[1]} - {r[2]}")
else:
    st.write("Nenhum compromisso registrado")

# Adicionar compromisso
st.subheader("Adicionar Compromisso")
titulo_comp = st.text_input("Título do Compromisso", key="titulo")
data_comp = st.text_input("Data (dd/mm ou dd/mm/yyyy)", key="data")
if st.button("Adicionar Compromisso"):
    if not titulo_comp.strip() or not data_comp.strip():
        st.warning("Informe título e data")
    else:
        try:
            data_texto = data_comp.replace(" ", "")
            if len(data_texto.split("/")) == 2:
                data_texto += f"/{datetime.now().year}"
            data_obj = datetime.strptime(data_texto, "%d/%m/%Y")
            data_formatada = data_obj.strftime("%d/%m/%Y")
            assistente.cursor.execute("INSERT INTO compromissos (titulo, data_hora) VALUES (?,?)",
                                      (titulo_comp, data_formatada))
            assistente.conn.commit()
            st.success(f"Compromisso '{titulo_comp}' adicionado para {data_formatada}")
        except:
            st.error("Formato de data inválido. Use dd/mm ou dd/mm/yyyy.")

# Excluir compromisso
st.subheader("Excluir Compromisso")
id_excluir = st.number_input("ID do Compromisso", min_value=1, step=1)
if st.button("Excluir Compromisso"):
    assistente.cursor.execute("SELECT * FROM compromissos WHERE id=?", (id_excluir,))
    row = assistente.cursor.fetchone()
    if row:
        assistente.cursor.execute("DELETE FROM compromissos WHERE id=?", (id_excluir,))
        assistente.conn.commit()
        st.success(f"Compromisso '{row[1]}' excluído com sucesso")
    else:
        st.warning("ID não encontrado")
