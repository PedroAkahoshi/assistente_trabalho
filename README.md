# Assistente Virtual **JOELMA**

JOELMA é um assistente virtual de automação voltado para fluxos internos de TI. Ele auxilia em gerenciamento de contatos, agenda com notificações automáticas, anotações, biblioteca de procedimentos, automações programadas, macros de inserção rápida e painel de acompanhamento (HUD), visando aumentar a produtividade e reduzir tarefas repetitivas.

## 🧠 Descrição Geral

### **Qual problema ele resolve**
- Reduz tarefas repetitivas feitas manualmente.
- Aumenta a velocidade no atendimento a chamados.
- Organiza informações de forma centralizada.
- Facilita a comunicação através de Scripts padronizados.
- Substitui processos manuais por fluxos automatizados.


### 🚀 **Tecnologias e Bibliotecas Utilizadas**
- **Python 3**
- **CustomTkinter** — Interface gráfica moderna
- **SQLite3** — Banco de dados local
- **Pyperclip** — Área de transferência (copiar/colar procedimentos)
- **Keyboard** — Atalhos globais de teclado e automações
- **Hashlib** — Criptografia de senhas (SHA-256)
- **Threading** — Execução de tarefas em segundo plano
- **Winsound** — Alertas sonoros no Windows
- **Webbrowser** — Abertura automática de sites e sistemas
- **Datetime** — Controle de datas e horários
- **OS / Sys / Shutil** — Manipulação de sistema e arquivos
- **Re (Regex)** — Validação e processamento de textos
- **Time** — Controle de temporização

### **Público-alvo**
- Equipes de TI
- Organizações com grande volume de chamados
- Automação de rotinas operacionais
- Uso pessoal para organização de tarefas

## ✨ Principais Funcionalidades

### 📅 Agendamento de compromissos
- Criar, listar e excluir compromissos
- Notificações automáticas com alerta sonoro
- Visualização de próximos eventos

### 📝 Sistema de anotações
- Criar, visualizar, atualizar e excluir anotações
- Registro de chamado, e-mail, status e descrição
- Histórico por perfil

### 📄 Macros
- Textos pré-escritos pelos usuários
- Agilizando o envio de mensagens

## 🏗️ Arquitetura

### Fluxo Geral
Usuário → Interface Gráfica (CustomTkinter) → Núcleo da Assistente → Banco de Dados SQLite

### Camadas
- Interface (CustomTkinter GUI)
- Lógica (agendamentos, notas, PDFs)
- Banco de Dados SQLite
- Manipulação externa (arquivos, áudio)

## ⚙️ Como Executar

### Pré-requisitos
- Python 3.10+
- Pip instalado

### Instalação
- Dentro do terminal, instale as bibliotecas através do comando

```bash
pip install customtkinter pyperclip keyboard
```

### Executar
- após isso execute o assistente no terminal utilizando o comando :

```bash
python joelma.py
```
### Comandos do Assistente

#### Perfil

* **ajuda**: após criar um perfil e abrir o chat, digite `ajuda` para visualizar os comandos disponíveis.
* **compromisso**: utilize os comandos `adicionar compromisso`, `listar compromisso` ou `excluir compromisso`.
* **anotação**: utilize os comandos `adicionar anotação`, `ver anotação`, `atualizar anotação` ou `excluir anotação`.

#### Procedimentos

* Clique em **📋 Procedimentos** no menu lateral.
* Digite `adicionar` para criar um novo procedimento.
* Informe um título e o conteúdo do procedimento.
* Utilize `listar` para visualizar os procedimentos cadastrados.
* Utilize `copiar` para enviar o conteúdo para a área de transferência.
* Utilize `excluir` para remover procedimentos cadastrados.

#### Atalho de Macros

* Pressione **Ctrl + Shift + U** para abrir a janela de macros.
* Selecione um procedimento cadastrado.
* O texto será copiado e inserido automaticamente no campo ativo.

## 📚 Exemplos de Uso

- Criar compromissos e receber lembretes automáticos
- Registrar anotações de chamados e atendimentos
- Armazenar procedimentos técnicos padronizados
- Utilizar macros para respostas rápidas
- Programar abertura automática de sistemas e sites
- Consultar informações através do painel HUD

