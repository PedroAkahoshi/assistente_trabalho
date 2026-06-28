import hashlib
import customtkinter as ctk
import os
import sys
import shutil
import re
import sqlite3
import threading
import winsound
from datetime import datetime
import webbrowser  
import pyperclip  
import time

# Biblioteca para os Atalhos Globais
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False

# ========================================== #
# CONFIGURAÇÕES VISUAIS
# ========================================== #
C = {
    "bg": ("#f1f5f9", "#0d1117"), 
    "sidebar": ("#e2e8f0", "#111827"), 
    "contacts": ("#cbd5e1", "#151d2b"),
    "input": ("#ffffff", "#1c2333"), 
    "msg_bot": ("#ffffff", "#1c2333"), 
    "msg_user": ("#0078FF", "#0078FF"),
    "contact_sel": ("#94a3b8", "#1e3a5f"), 
    "text": ("#0f172a", "#e6edf3"), 
    "text2": ("#64748b", "#8b949e"), 
    "blue": ("#0078FF", "#0078FF"), 
    "border": ("#cbd5e1", "#21262d"), 
    "green": ("#16a34a", "#3fb950"), 
    "red": ("#dc2626", "#f85149")
}
F = "Segoe UI"
ctk.set_appearance_mode("Dark")

# ========================================== #
# BACKEND
# ========================================== #
class Backend:
    def __init__(self):
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.abspath(os.path.dirname(__file__))

        self.PDF_FOLDER = os.path.join(self.base_dir, 'baixados_pdfs')
        self.DL_FOLDER = os.path.join(self.base_dir, 'procedimentos')
        
        os.makedirs(self.PDF_FOLDER, exist_ok=True)
        os.makedirs(self.DL_FOLDER, exist_ok=True)

        db_path = os.path.join(self.base_dir, "agenda.db")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.c = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        self.c.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT)")
        self.c.execute("CREATE TABLE IF NOT EXISTS contatos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, user_id INTEGER, data_criacao TEXT)")
        self.c.execute("CREATE TABLE IF NOT EXISTS msgs (id INTEGER PRIMARY KEY AUTOINCREMENT, cid INTEGER, texto TEXT, eu INTEGER, dt TEXT)")
        self.c.execute("CREATE TABLE IF NOT EXISTS compromissos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, data_hora TEXT, cid INTEGER)")
        
        self.c.execute("""CREATE TABLE IF NOT EXISTS anotacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, descricao TEXT, data_criacao TEXT, 
            chamado TEXT, status TEXT, status_op TEXT, cid INTEGER, email TEXT, data_chamado TEXT)""")
        
        self.c.execute("CREATE TABLE IF NOT EXISTS procedimentos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, descricao TEXT, user_id INTEGER)")
        
        self.c.execute("""CREATE TABLE IF NOT EXISTS rotinas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, hora TEXT, acao TEXT, parametro TEXT)""")
        
        try: self.c.execute("ALTER TABLE contatos ADD COLUMN user_id INTEGER")
        except: pass
        try: self.c.execute("ALTER TABLE procedimentos ADD COLUMN user_id INTEGER")
        except: pass
        try: self.c.execute("ALTER TABLE anotacoes ADD COLUMN email TEXT")
        except: pass
        try: self.c.execute("ALTER TABLE anotacoes ADD COLUMN data_chamado TEXT")
        except: pass
        
        self.conn.commit()

    def hash_senha(self, senha):
        return hashlib.sha256(senha.encode()).hexdigest()

    def verificar_login(self, usuario, senha):
        self.c.execute("SELECT id FROM usuarios WHERE usuario = ? AND senha = ?", (usuario, self.hash_senha(senha)))
        res = self.c.fetchone()
        return res[0] if res else None

    def excluir_usuario_completo(self, user_id):
        self.c.execute("SELECT id FROM contatos WHERE user_id = ?", (user_id,))
        perfis = self.c.fetchall()
        for (cid,) in perfis:
            for t in["msgs", "compromissos", "anotacoes"]:
                self.c.execute(f"DELETE FROM {t} WHERE cid = ?", (cid,))
                
        try: self.c.execute("DELETE FROM procedimentos WHERE user_id = ?", (user_id,))
        except: pass
        try: self.c.execute("DELETE FROM rotinas WHERE user_id = ?", (user_id,))
        except: pass

        self.c.execute("DELETE FROM contatos WHERE user_id = ?", (user_id,))
        self.c.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
        self.conn.commit()

# ========================================== #
# APP PRINCIPAL
# ========================================== #
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("⚡ Assistente Executivo Pro")
        self.geometry("1100x750")
        self.configure(fg_color=C["bg"])
        self.be = Backend()
        
        self.user_id = None
        self.cid = None
        self.fluxo = None
        self.fl_step = 0
        self.fl_dados = {}
        
        self.notificados = set()
        self.rotinas_executadas = set() 

        if KEYBOARD_AVAILABLE:
            keyboard.add_hotkey('ctrl+shift+u', lambda: self.after(0, self._abrir_janela_macros))

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True)

        self._show_login_screen()
        self._verificar_compromissos()
        self._verificar_rotinas()

    # ========================================== #
    # TELA DE HUD (PAINEL RÁPIDO)
    # ========================================== #
    def _abrir_tela_hud(self):
        if not self.user_id: return
        
        if hasattr(self, 'janela_hud') and self.janela_hud.winfo_exists():
            self.janela_hud.focus_force()
            return

        self.janela_hud = ctk.CTkToplevel(self)
        self.janela_hud.title("👁️ HUD - Painel Rápido")
        self.janela_hud.geometry("380x450")
        self.janela_hud.configure(fg_color=C["bg"])
        self.janela_hud.attributes("-topmost", True)
        self.janela_hud.focus_force()

        ctk.CTkLabel(self.janela_hud, text="👁️ Resumo Rápido", font=(F, 20, "bold"), text_color=C["blue"]).pack(pady=15)

        # 1. Buscar Próximo Evento (Futuro)
        self.be.c.execute("""
            SELECT comp.titulo, comp.data_hora, cont.nome 
            FROM compromissos comp
            JOIN contatos cont ON comp.cid = cont.id
            WHERE cont.user_id = ?
        """, (self.user_id,))
        
        agora = datetime.now()
        futuros =[]
        for tit, data_str, perfil in self.be.c.fetchall():
            try:
                dh_limpa = data_str.strip()
                try:
                    dt = datetime.strptime(dh_limpa, "%d/%m/%Y %H:%M")
                except ValueError:
                    dt = datetime.strptime(dh_limpa, "%d/%m %H:%M")
                    dt = dt.replace(year=agora.year)
                    
                if dt >= agora:
                    futuros.append((dt, tit, data_str, perfil))
            except: pass
        
        futuros.sort(key=lambda x: x[0]) # Ordena do mais próximo ao mais distante
        
        frame_evt = ctk.CTkFrame(self.janela_hud, fg_color=C["sidebar"], corner_radius=10)
        frame_evt.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(frame_evt, text="📅 Próximo Evento", font=(F, 14, "bold"), text_color=C["text"]).pack(anchor="w", padx=10, pady=(10, 5))
        
        if futuros:
            _, tit, d_str, perf = futuros[0]
            ctk.CTkLabel(frame_evt, text=f"📌 {tit}\n⏰ {d_str}   👤 {perf}", font=(F, 13), text_color=C["text2"], justify="left").pack(anchor="w", padx=10, pady=(0, 10))
        else:
            ctk.CTkLabel(frame_evt, text="Nenhum evento futuro agendado.", font=(F, 13), text_color=C["text2"]).pack(anchor="w", padx=10, pady=(0, 10))

        # 2. Buscar Última Anotação
        self.be.c.execute("""
            SELECT a.titulo, c.nome 
            FROM anotacoes a
            JOIN contatos c ON a.cid = c.id
            WHERE c.user_id = ?
            ORDER BY a.id DESC LIMIT 1
        """, (self.user_id,))
        nota = self.be.c.fetchone()
        
        frame_nota = ctk.CTkFrame(self.janela_hud, fg_color=C["sidebar"], corner_radius=10)
        frame_nota.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(frame_nota, text="📝 Última Anotação", font=(F, 14, "bold"), text_color=C["text"]).pack(anchor="w", padx=10, pady=(10, 5))
        
        if nota:
            ctk.CTkLabel(frame_nota, text=f"🏷️ {nota[0]}\n👤 Perfil: {nota[1]}", font=(F, 13), text_color=C["text2"], justify="left").pack(anchor="w", padx=10, pady=(0, 10))
        else:
            ctk.CTkLabel(frame_nota, text="Nenhuma anotação registrada.", font=(F, 13), text_color=C["text2"]).pack(anchor="w", padx=10, pady=(0, 10))

        # 3. Procedimento Recente
        self.be.c.execute("SELECT titulo FROM procedimentos WHERE user_id = ? ORDER BY id DESC LIMIT 1", (self.user_id,))
        proc = self.be.c.fetchone()

        frame_proc = ctk.CTkFrame(self.janela_hud, fg_color=C["sidebar"], corner_radius=10)
        frame_proc.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(frame_proc, text="📋 Procedimento Recente", font=(F, 14, "bold"), text_color=C["text"]).pack(anchor="w", padx=10, pady=(10, 5))
        
        if proc:
            ctk.CTkLabel(frame_proc, text=f"⚡ {proc[0]}", font=(F, 13), text_color=C["text2"]).pack(anchor="w", padx=10, pady=(0, 10))
        else:
            ctk.CTkLabel(frame_proc, text="Nenhum procedimento salvo.", font=(F, 13), text_color=C["text2"]).pack(anchor="w", padx=10, pady=(0, 10))

    # ========================================== #
    # MOTOR DE ROTINAS AUTOMÁTICAS
    # ========================================== #
    def _verificar_rotinas(self):
        if self.user_id:
            agora = datetime.now().strftime("%H:%M")
            hoje = datetime.now().strftime("%Y-%m-%d")
            
            self.be.c.execute("SELECT id, hora, acao, parametro FROM rotinas WHERE user_id = ?", (self.user_id,))
            for rid, hora, acao, parametro in self.be.c.fetchall():
                hash_exec = f"{rid}_{hoje}_{hora}" 
                
                if agora == hora and hash_exec not in self.rotinas_executadas:
                    self.rotinas_executadas.add(hash_exec)
                    self._executar_acao_rotina(acao, parametro)
                    
        self.after(30000, self._verificar_rotinas)

    def _executar_acao_rotina(self, acao, parametro):
        if acao == "Abrir Site/Sistema":
            try:
                if parametro.startswith("http"):
                    webbrowser.open_new_tab(parametro)
                else:
                    os.startfile(parametro) 
            except Exception as e:
                print(f"Erro ao executar rotina {parametro}: {e}")

    # ========================================== #
    # TELA DE GERENCIAMENTO DE ROTINAS
    # ========================================== #
    def _abrir_tela_rotinas(self):
        if not self.user_id: return
        
        if hasattr(self, 'janela_rotina') and self.janela_rotina.winfo_exists():
            self.janela_rotina.focus_force()
            return
            
        self.janela_rotina = ctk.CTkToplevel(self)
        self.janela_rotina.title("⏱️ Rotinas Automáticas")
        self.janela_rotina.geometry("600x600")
        self.janela_rotina.configure(fg_color=C["bg"])
        self.janela_rotina.attributes("-topmost", True)
        self.janela_rotina.focus_force()
        
        self.rotina_selecionada = None

        ctk.CTkLabel(self.janela_rotina, text="⏱️ Agendar Automações", font=(F, 20, "bold"), text_color=C["blue"]).pack(pady=(15, 5))

        form_frame = ctk.CTkFrame(self.janela_rotina, fg_color=C["sidebar"], corner_radius=10)
        form_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(form_frame, text="Hora (HH:MM):", font=(F, 13, "bold"), text_color=C["text"]).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        entry_hora = ctk.CTkEntry(form_frame, width=120, placeholder_text="Ex: 08:00")
        entry_hora.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        ctk.CTkLabel(form_frame, text="Ação Automática:", font=(F, 13, "bold"), text_color=C["text"]).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        combo_acao = ctk.CTkOptionMenu(form_frame, values=["Abrir Site/Sistema"])
        combo_acao.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(form_frame, text="Link ou Caminho:", font=(F, 13, "bold"), text_color=C["text"]).grid(row=2, column=0, padx=10, pady=10, sticky="w")
        entry_param = ctk.CTkEntry(form_frame, width=320, placeholder_text="Ex: https://tjsp.jus.br ou C:\\App.exe")
        entry_param.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        btn_frame = ctk.CTkFrame(self.janela_rotina, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=5)
        
        def atualizar_lista():
            for w in scroll.winfo_children(): w.destroy()
            self.be.c.execute("SELECT id, hora, acao, parametro FROM rotinas WHERE user_id=? ORDER BY hora ASC", (self.user_id,))
            rotinas = self.be.c.fetchall()
            
            if not rotinas:
                ctk.CTkLabel(scroll, text="Nenhuma rotina cadastrada.", text_color=C["text2"]).pack(pady=20)
                return

            for r_id, h, a, p in rotinas:
                card = ctk.CTkFrame(scroll, fg_color=C["sidebar"], corner_radius=8)
                card.pack(fill="x", pady=5)
                texto = f"⏰ {h}  |  {a}\n🔗 {p}"
                
                btn = ctk.CTkButton(card, text=texto, font=(F, 13), fg_color="transparent", text_color=C["text"], 
                                    anchor="w", hover_color=C["contact_sel"],
                                    command=lambda id_v=r_id, h_v=h, a_v=a, p_v=p: selecionar(id_v, h_v, a_v, p_v))
                btn.pack(fill="x", padx=10, pady=8)

        def selecionar(r_id, h, a, p):
            self.rotina_selecionada = r_id
            entry_hora.delete(0, "end"); entry_hora.insert(0, h)
            combo_acao.set(a)
            entry_param.delete(0, "end"); entry_param.insert(0, p)
            
            btn_add.configure(state="disabled")
            btn_upd.configure(state="normal", fg_color=C["blue"])
            btn_del.configure(state="normal", fg_color=C["red"])

        def limpar():
            self.rotina_selecionada = None
            entry_hora.delete(0, "end")
            entry_param.delete(0, "end")
            
            btn_add.configure(state="normal")
            btn_upd.configure(state="disabled", fg_color="gray")
            btn_del.configure(state="disabled", fg_color="gray")

        def validar_hora(h):
            return re.match(r"^\d{2}:\d{2}$", h) is not None

        def adicionar():
            h, a, p = entry_hora.get().strip(), combo_acao.get(), entry_param.get().strip()
            if not validar_hora(h): 
                entry_hora.delete(0, "end"); entry_hora.insert(0, "Use HH:MM"); return
            if h and p:
                self.be.c.execute("INSERT INTO rotinas (user_id, hora, acao, parametro) VALUES (?,?,?,?)", (self.user_id, h, a, p))
                self.be.conn.commit()
                limpar(); atualizar_lista()

        def atualizar():
            if self.rotina_selecionada:
                h, a, p = entry_hora.get().strip(), combo_acao.get(), entry_param.get().strip()
                if not validar_hora(h): return
                self.be.c.execute("UPDATE rotinas SET hora=?, acao=?, parametro=? WHERE id=?", (h, a, p, self.rotina_selecionada))
                self.be.conn.commit()
                limpar(); atualizar_lista()

        def excluir():
            if self.rotina_selecionada:
                self.be.c.execute("DELETE FROM rotinas WHERE id=?", (self.rotina_selecionada,))
                self.be.conn.commit()
                limpar(); atualizar_lista()
        
        btn_add = ctk.CTkButton(btn_frame, text="Adicionar", fg_color=C["green"], width=100, command=adicionar)
        btn_add.pack(side="left", padx=(0, 5))
        
        btn_upd = ctk.CTkButton(btn_frame, text="Atualizar", fg_color="gray", state="disabled", width=100, command=atualizar)
        btn_upd.pack(side="left", padx=5)
        
        btn_del = ctk.CTkButton(btn_frame, text="Excluir", fg_color="gray", state="disabled", width=100, command=excluir)
        btn_del.pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="Limpar", fg_color="transparent", border_width=1, text_color=C["text"], width=80, command=limpar).pack(side="right")

        scroll = ctk.CTkScrollableFrame(self.janela_rotina, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        
        atualizar_lista()

    # ========================================== #
    # MACROS E RESTANTE DO CÓDIGO
    # ========================================== #
    def _abrir_janela_macros(self):
        if not self.user_id: return
        if hasattr(self, 'janela_macro') and self.janela_macro.winfo_exists():
            self.janela_macro.focus_force()
            return
            
        self.janela_macro = ctk.CTkToplevel(self)
        self.janela_macro.title("⚡ Inserção Rápida (Macros)")
        self.janela_macro.geometry("450x550")
        self.janela_macro.configure(fg_color=C["bg"])
        self.janela_macro.attributes("-topmost", True)
        self.janela_macro.focus_force()

        ctk.CTkLabel(self.janela_macro, text="Escolha um Procedimento", font=(F, 18, "bold"), text_color=C["blue"]).pack(pady=15)

        scroll = ctk.CTkScrollableFrame(self.janela_macro, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.be.c.execute("SELECT titulo, descricao FROM procedimentos WHERE user_id=? ORDER BY id DESC", (self.user_id,))
        procedimentos = self.be.c.fetchall()

        if not procedimentos:
            ctk.CTkLabel(scroll, text="Você não tem nenhum procedimento cadastrado.", text_color=C["text2"]).pack(pady=20)
            return

        for tit, desc in procedimentos:
            card = ctk.CTkButton(scroll, text=f"⚡ {tit}", font=(F, 14, "bold"), 
                               fg_color=C["sidebar"], text_color=C["text"], hover_color=C["contact_sel"],
                               anchor="w", height=45,
                               command=lambda d=desc: self._executar_macro(d))
            card.pack(fill="x", pady=5)

    def _executar_macro(self, texto):
        if hasattr(self, 'janela_macro') and self.janela_macro.winfo_exists():
            self.janela_macro.destroy() 
        
        def digitar():
            time.sleep(0.4) 
            try: old_clipboard = pyperclip.paste()
            except: old_clipboard = ""
            pyperclip.copy(texto)
            keyboard.send("ctrl+v")
            time.sleep(0.5) 
            try: 
                if old_clipboard: pyperclip.copy(old_clipboard)
            except: pass

        threading.Thread(target=digitar, daemon=True).start()

    # ========================================== #
    # SISTEMA DE NOTIFICAÇÃO E AGENDAMENTOS
    # ========================================== #
    def _verificar_compromissos(self):
        if self.user_id:
            agora = datetime.now()
            self.be.c.execute("""
                SELECT comp.id, comp.titulo, comp.data_hora, cont.nome
                FROM compromissos comp
                JOIN contatos cont ON comp.cid = cont.id
                WHERE cont.user_id = ?
            """, (self.user_id,))
            
            for comp_id, titulo, data_hora, perfil in self.be.c.fetchall():
                try:
                    dh_limpa = data_hora.strip()
                    dt_comp = None
                    
                    # Tenta ler no formato completo (com ano) caso exista algum antigo salvo
                    try:
                        dt_comp = datetime.strptime(dh_limpa, "%d/%m/%Y %H:%M")
                    except ValueError:
                        # Se der erro, lê no seu formato (Dia/Mês Hora:Minuto) sem o ano
                        dt_comp = datetime.strptime(dh_limpa, "%d/%m %H:%M")
                        # Como não tem ano, o Python assume 1900. Injetamos o ano atual automaticamente!
                        dt_comp = dt_comp.replace(year=agora.year)
                    
                    # Calcula a diferença em segundos (se deu positivo, a hora chegou ou passou)
                    diferenca = (agora - dt_comp).total_seconds()
                    
                    # Se chegou a hora (0) ou atrasou até 1h (3600 seg) e ainda não apitou:
                    if 0 <= diferenca <= 3600 and comp_id not in self.notificados:
                        self.notificados.add(comp_id)
                        self._mostrar_alerta(titulo, perfil, data_hora)
                        
                except Exception as e:
                    # Fallback (Plano B): Se você digitou num formato muito diferente, ele tenta ler como texto
                    agora_str_com_ano = agora.strftime("%d/%m/%Y %H:%M")
                    agora_str_sem_ano = agora.strftime("%d/%m %H:%M")
                    
                    if (agora_str_com_ano in data_hora or agora_str_sem_ano in data_hora) and comp_id not in self.notificados:
                        self.notificados.add(comp_id)
                        self._mostrar_alerta(titulo, perfil, data_hora)

        # Checa a cada 20 segundos para não perder o minuto exato do compromisso
        self.after(20000, self._verificar_compromissos)

    def _mostrar_alerta(self, titulo, perfil, data_hora):
        # Toca o bipe do alarme em uma "thread" separada para não congelar o aparecimento do pop-up
        def tocar_alarme():
            try:
                winsound.Beep(1000, 300)
                winsound.Beep(1500, 400)
            except: pass
        
        threading.Thread(target=tocar_alarme, daemon=True).start()

        alerta = ctk.CTkToplevel(self)
        alerta.title("⏰ Lembrete de Evento")
        alerta.geometry("380x220")
        alerta.configure(fg_color=C["bg"])
        
        # Garante que a janela apareça na frente de tudo no Windows
        alerta.lift()
        alerta.attributes("-topmost", True)
        alerta.focus_force()
        
        ctk.CTkLabel(alerta, text="⏰ EVENTO AGORA", font=(F, 18, "bold"), text_color=C["red"]).pack(pady=(20, 10))
        ctk.CTkLabel(alerta, text=f"Perfil: {perfil}\n📌 {titulo}\n📅 {data_hora}", font=(F, 14), text_color=C["text"]).pack(pady=5)
        ctk.CTkButton(alerta, text="Entendido", command=alerta.destroy, fg_color=C["blue"], width=150).pack(pady=(15, 10))

    def _abrir_tela_eventos(self):
        if not self.user_id: return
            
        janela = ctk.CTkToplevel(self)
        janela.title("🔔 Todos os Eventos Agendados")
        janela.geometry("550x450")
        janela.configure(fg_color=C["bg"])
        janela.attributes("-topmost", True)
        janela.focus_force()

        ctk.CTkLabel(janela, text="Eventos Agendados", font=(F, 22, "bold"), text_color=C["text"]).pack(pady=15)

        scroll = ctk.CTkScrollableFrame(janela, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.be.c.execute("""
            SELECT comp.titulo, comp.data_hora, cont.nome 
            FROM compromissos comp
            JOIN contatos cont ON comp.cid = cont.id
            WHERE cont.user_id = ?
            ORDER BY comp.data_hora ASC
        """, (self.user_id,))
        
        eventos = self.be.c.fetchall()

        if not eventos:
            ctk.CTkLabel(scroll, text="Nenhum compromisso agendado no banco.", text_color=C["text2"]).pack(pady=20)
            return

        for tit, data, perfil in eventos:
            card = ctk.CTkFrame(scroll, fg_color=C["sidebar"], corner_radius=10)
            card.pack(fill="x", pady=5)
            ctk.CTkLabel(card, text=f"📌 {tit}", font=(F, 14, "bold"), text_color=C["text"]).pack(anchor="w", padx=15, pady=(10, 0))
            ctk.CTkLabel(card, text=f"📅 {data}  |  👤 Perfil: {perfil}", font=(F, 12), text_color=C["text2"]).pack(anchor="w", padx=15, pady=(0, 10))

    # ========================================== #
    # TELA DE GERENCIAMENTO DE PROCEDIMENTOS
    # ========================================== #
    def _abrir_tela_procedimentos(self):
        if not self.user_id: return
        
        janela = ctk.CTkToplevel(self)
        janela.title("📋 Gerenciador de Procedimentos")
        janela.geometry("550x650")
        janela.configure(fg_color=C["bg"])
        janela.attributes("-topmost", True)
        janela.focus_force()

        janela.fluxo = None
        janela.fl_step = 0
        janela.fl_dados = {}

        ctk.CTkLabel(janela, text="Procedimentos Salvos", font=(F, 20, "bold"), text_color=C["blue"]).pack(pady=10)

        msg_scroll = ctk.CTkScrollableFrame(janela, fg_color="transparent")
        msg_scroll.pack(fill="both", expand=True, padx=10, pady=5)

        input_bar = ctk.CTkFrame(janela, fg_color="transparent", height=70)
        input_bar.pack(fill="x", padx=20, pady=15)

        # Usando CTkTextbox para suportar as quebras de linha e altura ajustável
        entry = ctk.CTkTextbox(input_bar, height=45, corner_radius=22, wrap="word")
        entry.pack(side="left", fill="x", expand=True, padx=0)

        def render_msg(txt, eu):
            box = ctk.CTkFrame(msg_scroll, fg_color=C["msg_user"] if eu else C["msg_bot"], corner_radius=15)
            box.pack(anchor="e" if eu else "w", pady=5, padx=10)
            txt_color = "white" if eu else C["text"]
            ctk.CTkLabel(box, text=txt, wraplength=350, text_color=txt_color, justify="left").pack(padx=15, pady=8)
            msg_scroll._parent_canvas.yview_moveto(1.0)

        def bot(txt):
            render_msg(txt, False)

        bot("Olá! Bem-vindo ao chat de procedimentos padrão.\n\nComandos diretos disponíveis:\n🛠️ adicionar\n📋 copiar\n📄 listar\n🗑️ excluir")

        def flow_engine(r):
            if r.lower() in["cancelar", "sair"]: janela.fluxo = None; bot("Operação Cancelada."); return
            try:
                if janela.fluxo == "add_proc":
                    if janela.fl_step == 1: 
                        janela.fl_dados['t'] = r; janela.fl_step = 2; bot("Cole ou digite a mensagem de procedimento:")
                    elif janela.fl_step == 2:
                        self.be.c.execute("INSERT INTO procedimentos (titulo, descricao, user_id) VALUES (?,?,?)", (janela.fl_dados['t'], r, self.user_id))
                        self.be.conn.commit(); bot("✅ Procedimento salvo com sucesso!"); janela.fluxo = None
                        
                elif janela.fluxo == "ver_proc":
                    idx = int(re.search(r"\d+", r).group()) - 1
                    item = janela.fl_dados['list'][idx]
                    bot(f"🛠️ {item[1]}\n\n{item[2]}"); janela.fluxo = None
                    
                elif janela.fluxo == "copy_proc":
                    idx = int(re.search(r"\d+", r).group()) - 1
                    item = janela.fl_dados['list'][idx]
                    pyperclip.copy(item[2])
                    bot(f"✅ O texto de '{item[1]}' foi copiado!\nÉ só dar Ctrl+V onde precisar."); janela.fluxo = None
                    
                elif janela.fluxo == "del_proc":
                    idx = int(re.search(r"\d+", r).group()) - 1
                    item = janela.fl_dados['list'][idx]
                    self.be.c.execute("DELETE FROM procedimentos WHERE id=?", (item[0],))
                    self.be.conn.commit()
                    bot("✅ Procedimento excluído do banco de dados."); janela.fluxo = None
            except: bot("❌ Opção inválida ou número não encontrado."); janela.fluxo = None

        # --- FUNÇÕES DE CONTROLE DE ALTURA DA CAIXA DE TEXTO (PROCEDIMENTOS) ---
        def ajustar_altura_proc(event=None):
            texto = entry.get("1.0", "end-1c")
            linhas_manuais = texto.count("\n")
            linhas_wrap = sum(len(linha) // 50 for linha in texto.split("\n"))
            total_linhas = 1 + linhas_manuais + linhas_wrap
            
            nova_altura = min(45 + (total_linhas - 1) * 25, 150)
            
            if entry.cget("height") != nova_altura:
                entry.configure(height=nova_altura)
                entry.see("insert")

        def pular_linha_proc(event=None):
            entry.insert("insert", "\n")
            ajustar_altura_proc()
            return "break"
        # ---------------------------------------------------------

        def process_input(event=None):
            # Ler e limpar o textbox adequadamente
            txt = entry.get("1.0", "end-1c").strip()
            if not txt: return "break"
            
            entry.delete("1.0", "end")
            entry.configure(height=45) # Restaura a altura na hora de enviar
            render_msg(txt, True)

            if janela.fluxo:
                flow_engine(txt)
                return "break"

            cmd = txt.lower()
            janela.fl_dados = {}

            if "ajuda" in cmd:
                bot("Comandos da janela:\n- adicionar\n- listar\n- copiar\n- excluir")
            elif "adicionar" in cmd:
                janela.fluxo = "add_proc"; janela.fl_step = 1; bot("Qual o título/assunto deste procedimento?")
            elif "listar" in cmd:
                self.be.c.execute("SELECT id, titulo, descricao FROM procedimentos WHERE user_id=? ORDER BY id DESC", (self.user_id,))
                janela.fl_dados['list'] = self.be.c.fetchall()
                if janela.fl_dados['list']: 
                    janela.fluxo = "ver_proc"
                    bot("Qual o número do procedimento que você quer ver?\n" + "\n".join([f"{i+1}. {r[1]}" for i,r in enumerate(janela.fl_dados['list'])]))
                else: bot("Nenhum procedimento salvo no banco.")
            elif "copiar" in cmd:
                self.be.c.execute("SELECT id, titulo, descricao FROM procedimentos WHERE user_id=? ORDER BY id DESC", (self.user_id,))
                janela.fl_dados['list'] = self.be.c.fetchall()
                if janela.fl_dados['list']: 
                    janela.fluxo = "copy_proc"
                    bot("Qual o número do procedimento que deseja copiar?\n" + "\n".join([f"{i+1}. {r[1]}" for i,r in enumerate(janela.fl_dados['list'])]))
                else: bot("Nenhum procedimento salvo no banco.")
            elif "excluir" in cmd:
                self.be.c.execute("SELECT id, titulo FROM procedimentos WHERE user_id=? ORDER BY id DESC", (self.user_id,))
                janela.fl_dados['list'] = self.be.c.fetchall()
                if not janela.fl_dados['list']: 
                    bot("Nada para excluir."); return "break"
                janela.fluxo = "del_proc"
                bot("Qual o número do procedimento para excluir?\n" + "\n".join([f"{i+1}. {r[1]}" for i,r in enumerate(janela.fl_dados['list'])]))
            else:
                bot("Não entendi. Os comandos aqui são focados em procedimentos. Digite 'adicionar', 'listar', 'copiar' ou 'excluir'.")
            
            return "break"

        # Aplicando os "binds" de teclado na caixa de input
        entry.bind("<Return>", process_input)
        entry.bind("<Shift-Return>", pular_linha_proc)
        entry.bind("<KeyRelease>", ajustar_altura_proc)

    def _abrir_ferramentas_suporte(self):
        sites =[
            "https://suporte.tjsp.jus.br/saw/Requests",
            "https://apps.powerapps.com/play/e/98c9177a-56c9-4700-b399-91d21c88f93b/a/880c8aa3-24b7-4306-bea8-54709d6c4528?tenantId=3590422d-8e59-4036-9245-d6edd8cc0f7a&hint=fa9b7bb3-9301-47a4-b34b-f30477ee36b6&source=sharebutton&sourcetime=1702993302295",
            "https://www.tjsp.jus.br/jud/tjspcalc/"
        ]
        for site in sites:
            webbrowser.open_new_tab(site)

    def _limpar_tela(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()
        self.main_container.grid_columnconfigure((0,1,2), weight=0)
        self.main_container.grid_rowconfigure(0, weight=0)

    def _toggle_tema(self):
        if ctk.get_appearance_mode() == "Dark":
            ctk.set_appearance_mode("Light")
        else:
            ctk.set_appearance_mode("Dark")

    def _show_login_screen(self):
        self._limpar_tela()
        self.user_id = None
        self.cid = None
        
        f = ctk.CTkFrame(self.main_container, fg_color=C["sidebar"], width=380, height=480, corner_radius=15)
        f.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(f, text="ASSISTENTE PRO", font=(F, 24, "bold"), text_color=C["blue"]).pack(pady=(40, 20))
        
        self.u_entry = ctk.CTkEntry(f, placeholder_text="Usuário", width=280, height=40)
        self.u_entry.pack(pady=10)
        self.p_entry = ctk.CTkEntry(f, placeholder_text="Senha", width=280, height=40, show="*")
        self.p_entry.pack(pady=10)
        
        self.info_lab = ctk.CTkLabel(f, text="", text_color=C["red"], font=(F, 12))
        self.info_lab.pack()

        ctk.CTkButton(f, text="Entrar", fg_color=C["blue"], width=280, height=45, command=self._login_acao).pack(pady=10)
        ctk.CTkButton(f, text="Criar Nova Conta", fg_color="transparent", text_color=C["text"], border_width=1, width=280, height=45, command=self._registrar_acao).pack(pady=5)

    def _login_acao(self):
        uid = self.be.verificar_login(self.u_entry.get(), self.p_entry.get())
        if uid:
            self.user_id = uid
            self._build_main_ui()
        else:
            self.info_lab.configure(text="Usuário ou senha incorretos!", text_color=C["red"])

    def _registrar_acao(self):
        u, p = self.u_entry.get(), self.p_entry.get()
        if len(u) < 3: self.info_lab.configure(text="Mínimo 3 caracteres!"); return
        try:
            self.be.c.execute("INSERT INTO usuarios (usuario, senha) VALUES (?,?)", (u, self.be.hash_senha(p)))
            self.be.conn.commit()
            self.info_lab.configure(text="Conta criada! Pode entrar.", text_color=C["green"])
        except:
            self.info_lab.configure(text="Usuário já existe!", text_color=C["red"])

    def _build_main_ui(self):
        self._limpar_tela()
        self.main_container.grid_columnconfigure(2, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        s = ctk.CTkFrame(self.main_container, width=200, fg_color=C["sidebar"], corner_radius=0)
        s.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(s, text="⚡ MENU", font=(F, 18, "bold"), text_color=C["blue"]).pack(pady=20)
        
        for i, t, cmd in[("💬","Chat","ajuda"), ("📄","PDFs","listar pdf"), ("📅","Agenda","listar compromisso"), ("📝","Notas","ver anotação")]:
            ctk.CTkButton(s, text=f"{i} {t}", fg_color="transparent", text_color=C["text"], anchor="w", command=lambda c=cmd: self._process_input(c)).pack(fill="x", padx=10, pady=2)
            
        ctk.CTkButton(s, text="🔔 Eventos", fg_color="transparent", text_color=C["text"], anchor="w", command=self._abrir_tela_eventos).pack(fill="x", padx=10, pady=2)
        ctk.CTkButton(s, text="🛠️ Ferramentas", fg_color="transparent", text_color=C["text"], anchor="w", command=self._abrir_ferramentas_suporte).pack(fill="x", padx=10, pady=2)
        ctk.CTkButton(s, text="📋 Procedimentos", fg_color="transparent", text_color=C["text"], anchor="w", command=self._abrir_tela_procedimentos).pack(fill="x", padx=10, pady=2)
        ctk.CTkButton(s, text="⏱️ Rotinas", fg_color="transparent", text_color=C["text"], anchor="w", command=self._abrir_tela_rotinas).pack(fill="x", padx=10, pady=2)
        ctk.CTkButton(s, text="👁️ HUD", fg_color="transparent", text_color=C["text"], anchor="w", command=self._abrir_tela_hud).pack(fill="x", padx=10, pady=2)
        
        bot_side = ctk.CTkFrame(s, fg_color="transparent")
        bot_side.pack(side="bottom", fill="x", pady=20)
        
        ctk.CTkButton(bot_side, text="🌗 Tema", fg_color="transparent", text_color=C["text"], command=self._toggle_tema).pack(fill="x", padx=10, pady=(0,5))
        ctk.CTkButton(bot_side, text="🚪 Logout", fg_color="transparent", text_color=C["text"], command=self._show_login_screen).pack(fill="x", padx=10, pady=(0,5))
        ctk.CTkButton(bot_side, text="⚠️ Excluir Conta", text_color=C["red"], fg_color="transparent", command=self._delete_account_full).pack(fill="x", padx=10)

        self.cont_frame = ctk.CTkFrame(self.main_container, width=280, fg_color=C["contacts"], corner_radius=0)
        self.cont_frame.grid(row=0, column=1, sticky="nsew")
        hdr = ctk.CTkFrame(self.cont_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(hdr, text="Perfis", font=(F, 16, "bold"), text_color=C["text"]).pack(side="left")
        ctk.CTkButton(hdr, text="+", width=30, command=self._novo_contato).pack(side="right")
        self.list_scroll = ctk.CTkScrollableFrame(self.cont_frame, fg_color="transparent")
        self.list_scroll.pack(fill="both", expand=True)

        self.chat_frame = ctk.CTkFrame(self.main_container, fg_color=C["bg"], corner_radius=0)
        self.chat_frame.grid(row=0, column=2, sticky="nsew")
        self.msg_scroll = ctk.CTkScrollableFrame(self.chat_frame, fg_color="transparent")
        self.msg_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.input_bar = ctk.CTkFrame(self.chat_frame, fg_color="transparent", height=70)
        self.input_bar.pack(fill="x", padx=20, pady=20)
        
        self.entry = ctk.CTkTextbox(self.input_bar, height=45, corner_radius=22, state="disabled", wrap="word")
        self.entry.pack(side="left", fill="x", expand=True, padx=0)
        
        self.entry.bind("<Return>", self._send_text)
        self.entry.bind("<Shift-Return>", self._pular_linha)
        self.entry.bind("<KeyRelease>", self._ajustar_altura) 

        self._load_contacts()

    def _delete_account_full(self):
        d = ctk.CTkInputDialog(text="Digite DELETAR para apagar sua conta e dados:", title="Confirmação")
        res = d.get_input()
        if res and res.upper() == "DELETAR":
            self.be.excluir_usuario_completo(self.user_id)
            self._show_login_screen()

    def _load_contacts(self):
        for w in self.list_scroll.winfo_children(): w.destroy()
        self.be.c.execute("SELECT id, nome FROM contatos WHERE user_id = ? ORDER BY nome", (self.user_id,))
        for cid, nome in self.be.c.fetchall():
            f = ctk.CTkFrame(self.list_scroll, fg_color="transparent")
            f.pack(fill="x", padx=5, pady=2)
            bg = C["contact_sel"] if cid == self.cid else "transparent"
            
            btn = ctk.CTkButton(f, text=nome, fg_color=bg, text_color=C["text"], anchor="w", height=35, 
                                command=lambda id_perfil=cid: self.after(10, self._select_contact, id_perfil))
            btn.pack(side="left", fill="x", expand=True)
            
            ctk.CTkButton(f, text="🗑️", width=30, height=30, fg_color="transparent", text_color=C["text"],
                          command=lambda id_p=cid, nm=nome: self.after(10, self._remover_contato, id_p, nm)).pack(side="right")

    def _novo_contato(self):
        d = ctk.CTkInputDialog(text="Nome do Perfil:", title="Novo")
        nome = d.get_input()
        if nome:
            self.be.c.execute("INSERT INTO contatos (nome, user_id, data_criacao) VALUES (?, ?, ?)", 
                             (nome.strip(), self.user_id, datetime.now().strftime("%d/%m/%Y")))
            self.be.conn.commit(); self._load_contacts()

    def _remover_contato(self, cid, nome):
        d = ctk.CTkInputDialog(text=f"Digite SIM para excluir '{nome}':", title="Confirmar")
        res = d.get_input()
        if res and res.upper() == "SIM":
            for t in["msgs", "compromissos", "anotacoes", "contatos"]:
                self.be.c.execute(f"DELETE FROM {t} WHERE {'cid' if t!='contatos' else 'id'}=?", (cid,))
            self.be.conn.commit()
            
            if self.cid == cid: 
                self.cid = None
                self.entry.configure(state="disabled")
                for w in self.msg_scroll.winfo_children(): w.destroy()
            self._load_contacts()

    def _select_contact(self, cid):
        self.cid = cid
        self.fluxo = None
        for w in self.msg_scroll.winfo_children(): w.destroy()

        self.be.c.execute("SELECT texto, eu FROM msgs WHERE cid=? ORDER BY id ASC", (cid,))
        for txt, eu in self.be.c.fetchall():
            self._render_msg(txt, bool(eu), save_db=False, scroll=False)

        self._load_contacts()
        self.entry.configure(state="normal")
        self.after(100, self._force_focus_and_scroll)

    def _force_focus_and_scroll(self):
        self.lift()
        self.focus_force()
        self.msg_scroll._parent_canvas.yview_moveto(1.0)
        self.entry.focus_force()

    def _render_msg(self, txt, eu, save_db=True, scroll=True):
        box = ctk.CTkFrame(self.msg_scroll, fg_color=C["msg_user"] if eu else C["msg_bot"], corner_radius=15)
        box.pack(anchor="e" if eu else "w", pady=5, padx=10)
        
        txt_color = "white" if eu else C["text"]
        ctk.CTkLabel(box, text=txt, wraplength=400, text_color=txt_color, justify="left").pack(padx=15, pady=8)
        
        if save_db and self.cid:
            self.be.c.execute("INSERT INTO msgs (cid, texto, eu, dt) VALUES (?,?,?,?)", (self.cid, txt, 1 if eu else 0, datetime.now().strftime("%H:%M")))
            self.be.conn.commit()
        if scroll: self.after(10, self._scroll_to_bottom)

    def _bot(self, txt):
        if self.cid: 
            self._render_msg(txt, False)

    def _scroll_to_bottom(self): 
        self.msg_scroll._parent_canvas.yview_moveto(1.0)
    
    # --- FUNÇÕES DE CONTROLE DE ALTURA DA CAIXA DE TEXTO ---
    def _ajustar_altura(self, event=None):
        texto = self.entry.get("1.0", "end-1c")
        
        # Conta quebras de linha manuais (Shift+Enter)
        linhas_manuais = texto.count("\n")
        
        # Estima quebras automáticas (ajustado de 60 para 50 para evitar cortes)
        linhas_wrap = sum(len(linha) // 50 for linha in texto.split("\n"))
        
        total_linhas = 1 + linhas_manuais + linhas_wrap
        
        # Base = 45px. Cada linha extra ganha 25px (em vez de 20px, para o texto não sumir)
        nova_altura = min(45 + (total_linhas - 1) * 25, 150)
        
        # SÓ ATUALIZA A TELA SE A ALTURA REALMENTE MUDAR (Isso acaba com o pisca-pisca!)
        if self.entry.cget("height") != nova_altura:
            self.entry.configure(height=nova_altura)
            self.entry.see("insert") # Garante que a barra de rolagem acompanhe o cursor

    def _send_text(self, event=None):
        t = self.entry.get("1.0", "end-1c").strip()
        if t: 
            self.entry.delete("1.0", "end")
            self.entry.configure(height=45)  # Restaura instantaneamente para 1 linha
            self._process_input(t)
            self.entry.focus_force() 
        return "break"
        
    def _pular_linha(self, event=None):
        self.entry.insert("insert", "\n")
        self._ajustar_altura()
        return "break"
    # ---------------------------------------------------------

    def _process_input(self, txt):
        if not self.cid: return
        if self.fluxo: self._render_msg(txt, True); self._flow_engine(txt); return
        
        self._render_msg(txt, True)
        cmd = txt.lower()
        self.fl_dados = {}

        if "ajuda" in cmd or "comando" in cmd:
            self._bot("📄 listar pdf / baixar pdf\n📅 adicionar/listar/excluir compromisso\n📝 adicionar/ver/atualizar/excluir anotação")
        elif "listar" in cmd and "pdf" in cmd:
            pdfs =[f for f in os.listdir(self.be.PDF_FOLDER) if f.lower().endswith(".pdf")]
            self._bot("📄 PDFs:\n" + "\n".join([f"{i+1}. {p}" for i,p in enumerate(pdfs)]) if pdfs else "Pasta de PDFs vazia.")
        elif "baixar" in cmd and "pdf" in cmd:
            pdfs =[f for f in os.listdir(self.be.PDF_FOLDER) if f.lower().endswith(".pdf")]
            if pdfs: self.fluxo = "dl_pdf"; self.fl_dados['list'] = pdfs; self._bot("Qual o número do PDF?")
            else: self._bot("Nenhum PDF encontrado.")
        elif "adicionar" in cmd and "compromisso" in cmd:
            self.fluxo = "add_comp"; self.fl_step = 1; self._bot("Título do compromisso?")
        elif "listar" in cmd and "compromisso" in cmd:
            self.be.c.execute("SELECT titulo, data_hora FROM compromissos WHERE cid=?", (self.cid,))
            res = self.be.c.fetchall()
            self._bot("📅 Agenda:\n" + "\n".join([f"• {r[0]} ({r[1]})" for r in res]) if res else "Agenda vazia.")
        elif "excluir" in cmd and "compromisso" in cmd:
            self.be.c.execute("SELECT id, titulo FROM compromissos WHERE cid=?", (self.cid,))
            self.fl_dados['list'] = self.be.c.fetchall()
            if not self.fl_dados['list']: self._bot("Nada para excluir."); return
            self.fluxo = "del_comp"
            self._bot("Qual o número do compromisso para excluir?\n" + "\n".join([f"{i+1}. {r[1]}" for i,r in enumerate(self.fl_dados['list'])]))
        
        elif "adicionar" in cmd and "anota" in cmd:
            self.fluxo = "add_nota"; self.fl_step = 1; self._bot("Qual o título da nota?")
            
        elif "ver" in cmd and "anota" in cmd:
            self.be.c.execute("SELECT id, titulo, chamado, descricao, email, data_chamado, status FROM anotacoes WHERE cid=? ORDER BY id DESC", (self.cid,))
            self.fl_dados['list'] = self.be.c.fetchall()
            if self.fl_dados['list']: 
                self.fluxo = "ver_nota"
                self._bot("Número da nota que deseja ver?\n" + "\n".join([f"{i+1}. {r[1]}" for i,r in enumerate(self.fl_dados['list'])]))
            else: self._bot("Nenhuma nota salva.")
            
        elif "atualizar" in cmd and "anota" in cmd:
            self.be.c.execute("SELECT id, titulo FROM anotacoes WHERE cid=? ORDER BY id DESC", (self.cid,))
            self.fl_dados['list'] = self.be.c.fetchall()
            if not self.fl_dados['list']: 
                self._bot("Nenhuma nota para atualizar."); return
            self.fluxo = "upd_nota_field"
            self._bot("Qual o número da nota que deseja atualizar?\n" + "\n".join([f"{i+1}. {r[1]}" for i,r in enumerate(self.fl_dados['list'])]))
            
        elif "excluir" in cmd and "anota" in cmd:
            self.be.c.execute("SELECT id, titulo FROM anotacoes WHERE cid=?", (self.cid,))
            self.fl_dados['list'] = self.be.c.fetchall()
            if not self.fl_dados['list']: self._bot("Nada para excluir."); return
            self.fluxo = "del_nota"
            self._bot("Qual número deseja excluir?\n" + "\n".join([f"{i+1}. {r[1]}" for i,r in enumerate(self.fl_dados['list'])]))
        else:
            self._bot("Não entendi. Tente 'ajuda'.")

    # --- MOTOR DE FLUXOS (PASSOS) ---
    def _flow_engine(self, r):
        if r.lower() in["cancelar", "sair"]: self.fluxo = None; self._bot("Cancelado."); return
        try:
            if self.fluxo == "dl_pdf":
                idx = int(re.search(r"\d+", r).group()) - 1
                sel = self.fl_dados['list'][idx]
                shutil.copy2(os.path.join(self.be.PDF_FOLDER, sel), os.path.join(self.be.DL_FOLDER, sel))
                self._bot(f"✅ Arquivo '{sel}' movido!"); self.fluxo = None
                
            elif self.fluxo == "add_comp":
                if self.fl_step == 1: 
                    self.fl_dados['t'] = r; self.fl_step = 2
                    # Pede no formato reduzido: Dia/Mês Hora:Minuto
                    exemplo = datetime.now().strftime("%d/%m %H:%M")
                    self._bot(f"Data e Hora? (Exemplo: {exemplo})")
                elif self.fl_step == 2:
                    self.be.c.execute("INSERT INTO compromissos (titulo, data_hora, cid) VALUES (?,?,?)", (self.fl_dados['t'], r, self.cid))
                    self.be.conn.commit(); self._bot("✅ Agendado!"); self.fluxo = None
            
            elif self.fluxo == "del_comp":
                idx = int(re.search(r"\d+", r).group()) - 1
                item = self.fl_dados['list'][idx]
                self.be.c.execute("DELETE FROM compromissos WHERE id=?", (item[0],))
                self.be.conn.commit(); self._bot("✅ Compromisso removido."); self.fluxo = None
                    
            elif self.fluxo == "add_nota":
                if self.fl_step == 1: 
                    self.fl_dados['t'] = r; self.fl_step = 2; self._bot("Qual o e-mail da pessoa?")
                elif self.fl_step == 2:
                    self.fl_dados['email'] = r; self.fl_step = 3; self._bot("Qual o número do chamado (ou '-')?")
                elif self.fl_step == 3:
                    self.fl_dados['ch'] = r; self.fl_step = 4
                    exemplo_dt = datetime.now().strftime("%d/%m/%Y")
                    self._bot(f"Qual a data do chamado? (Exemplo: {exemplo_dt})")
                elif self.fl_step == 4:
                    self.fl_dados['dt_ch'] = r; self.fl_step = 5; self._bot("Qual o status da anotação/chamado?")
                elif self.fl_step == 5:
                    self.fl_dados['st'] = r; self.fl_step = 6; self._bot("Por fim, digite a descrição da anotação:")
                elif self.fl_step == 6:
                    self.be.c.execute("""INSERT INTO anotacoes 
                        (titulo, email, chamado, data_chamado, status, descricao, cid) 
                        VALUES (?,?,?,?,?,?,?)""", 
                        (self.fl_dados['t'], self.fl_dados['email'], self.fl_dados['ch'], 
                         self.fl_dados['dt_ch'], self.fl_dados['st'], r, self.cid))
                    self.be.conn.commit(); self._bot("✅ Nota salva com sucesso!"); self.fluxo = None

            elif self.fluxo == "ver_nota":
                idx = int(re.search(r"\d+", r).group()) - 1
                item = self.fl_dados['list'][idx]
                email_str = item[4] if item[4] else "Não informado"
                dt_str = item[5] if item[5] else "Não informada"
                status_str = item[6] if item[6] else "Não informado"
                
                msg = f"📝 Título: {item[1]}\n📧 E-mail: {email_str}\n📞 Chamado: {item[2]}\n📅 Data: {dt_str}\n📊 Status: {status_str}\n\n{item[3]}"
                self._bot(msg); self.fluxo = None
            
            elif self.fluxo == "upd_nota_field":
                idx = int(re.search(r"\d+", r).group()) - 1
                item = self.fl_dados['list'][idx]
                self.fl_dados['nota_id'] = item[0]
                self._bot("O que você quer alterar?\n1. Título\n2. E-mail\n3. Chamado\n4. Data\n5. Status\n6. Descrição")
                self.fluxo = "upd_nota_val"
                
            elif self.fluxo == "upd_nota_val":
                op = int(re.search(r"\d+", r).group())
                campos_bd = {1: "titulo", 2: "email", 3: "chamado", 4: "data_chamado", 5: "status", 6: "descricao"}
                nomes_exib = {1: "Título", 2: "E-mail", 3: "Chamado", 4: "Data", 5: "Status", 6: "Descrição"}
                
                if op not in campos_bd:
                    self._bot("❌ Opção de campo inválida. Tente novamente.")
                    self.fluxo = None
                else:
                    self.fl_dados['campo_db'] = campos_bd[op]
                    self.fl_dados['nome_campo'] = nomes_exib[op]
                    self._bot(f"Digite o novo conteúdo para '{nomes_exib[op]}':")
                    self.fluxo = "upd_nota_fim"
                    
            elif self.fluxo == "upd_nota_fim":
                campo = self.fl_dados['campo_db']
                nota_id = self.fl_dados['nota_id']
                self.be.c.execute(f"UPDATE anotacoes SET {campo}=? WHERE id=?", (r, nota_id))
                self.be.conn.commit()
                self._bot(f"✅ O campo '{self.fl_dados['nome_campo']}' foi atualizado com sucesso!")
                self.fluxo = None

            elif self.fluxo == "del_nota":
                idx = int(re.search(r"\d+", r).group()) - 1
                item = self.fl_dados['list'][idx]
                self.be.c.execute("DELETE FROM anotacoes WHERE id=?", (item[0],))
                self.be.conn.commit(); self._bot("✅ Nota excluída."); self.fluxo = None
                
        except Exception as e: 
            print("Erro:", e)
            self._bot("❌ Número inválido ou erro. Operação cancelada."); self.fluxo = None


if __name__ == "__main__":
    App().mainloop()