# app.py
import re
from flask import Flask, render_template, request, jsonify, session
from ALEXA1.ALEXA1.joelma import AssistentePDF # Importação corrigida
import os

# Inicializa Flask
app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
# Chave secreta é necessária para usar 'session'
app.secret_key = 'sua-chave-secreta-aqui' 

# Configuração das pastas (mais flexível)
PDF_STORAGE_PATH = "pdfs_storage"
DOWNLOAD_PATH = "downloads"

# Instancia o assistente com os caminhos definidos
assistente = AssistentePDF(pdf_folder=PDF_STORAGE_PATH, download_folder=DOWNLOAD_PATH)

# Página inicial
@app.route("/")
def index():
    # Limpa o estado da sessão quando o usuário carrega a página inicial
    session.pop('esperando_comando', None)
    return render_template("index.html")

# Rota para receber mensagens do frontend
@app.route("/send_message", methods=["POST"])
def send_message():
    data = request.get_json()
    msg = data.get("message", "").strip().lower()
    response = processar_comando(msg)
    return jsonify({"response": response})

# Função principal para processar comandos
def processar_comando(msg):
    # Limpa pontuação final indesejada
    msg_limpa = re.sub(r'[?.!;]$', '', msg).strip()

    # Verifica se há um comando pendente na SESSÃO do usuário
    if session.get('esperando_comando'):
        estado_pendente = session.pop('esperando_comando', None) # Pega e remove o estado

        if estado_pendente == "baixar_pdf":
            # A lógica de adicionar ".pdf" e tratar o nome foi movida para a classe
            resultado = assistente.baixar_pdf(msg_limpa)
            return resultado

    # --- Comandos iniciais ---
    if msg_limpa.startswith("listar pdf"):
        pdfs = assistente.listar_pdfs()
        if pdfs:
            return "PDFs disponíveis:\n- " + "\n- ".join(pdfs)
        else:
            return "Nenhum PDF encontrado na pasta de armazenamento."

    if msg_limpa.startswith("baixar pdf") or msg_limpa.startswith("baixar"):
        # Armazena o estado na SESSÃO do usuário
        session['esperando_comando'] = "baixar_pdf"
        return "Qual PDF você deseja baixar? (basta digitar o nome)"

    if "ajuda" in msg_limpa:
        return (
            "📋 Comandos disponíveis:\n"
            "- listar pdf\n"
            "- baixar pdf\n"
            "- ajuda\n"
            "- sair"
        )

    if msg_limpa in ["oi", "olá", "ola"]:
        return "Olá! 🤖 Estou pronta para te ajudar. Digite 'ajuda' para ver o que posso fazer."

    if msg_limpa in ["sair", "encerrar"]:
        return "Encerrando sessão. Até logo!"

    return "Comando não reconhecido. Digite 'ajuda' para ver os comandos disponíveis."

# Executar aplicação
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
