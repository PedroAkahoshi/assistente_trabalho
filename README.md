# Assistente Virtual **JOELMA**

JOELMA é uma assistente virtual desenvolvida durante o estágio de TI no Tribunal de Justiça, criada com o objetivo de otimizar o atendimento de chamados e automatizar tarefas rotineiras do setor de tecnologia. O sistema reduz operações manuais como agendamento, registro de informações e geração de documentos, oferecendo rapidez, organização e precisão no fluxo de trabalho.

## 🧠 Descrição Geral

### **O que é o assistente virtual**
JOELMA é um assistente virtual de automação voltado para fluxos internos de TI. Ele auxilia na organização de compromissos, gerenciamento de notas, fornecimento de documentos pré-formatados e alternância entre modos de digitação e voz.

### **Qual problema ele resolve**
- Reduz tarefas repetitivas feitas manualmente.
- Aumenta a velocidade no atendimento a chamados.
- Organiza informações de forma centralizada.
- Facilita a comunicação através de PDFs padronizados.
- Substitui processos manuais por fluxos automatizados.

### **Tecnologias utilizadas**
- **Python**
- **speech_recognition**, **pyttsx3**, **winsound**
- **sqlite3**
- **colorama**
- **os**, **shutil**
- **re**, **datetime**
- **pdfplumber**

### **Público-alvo**
- Equipes de TI
- Organizações com grande volume de chamados
- Automação de rotinas operacionais
- Uso pessoal para organização de tarefas

## ✨ Principais Funcionalidades

### 📅 Agendamento de compromissos
- Criar, editar e cancelar agendamentos
- Organização por data e horário

### 📝 Sistema de anotações
- Criar, listar, atualizar e excluir notas
- Organização por tags, datas ou categorias

### 📄 PDFs prontos
- PDFs usados no dia a dia (Petrus, F.A Dipol, robôs de automação)
- Possibilidade de personalização futura

### 🎙️ Modo voz e digitação
- Reconhecimento de voz
- Respostas por áudio
- Alternância dinâmica entre modos

## 🏗️ Arquitetura

### Fluxo Geral
Usuário → Interface CLI → Núcleo da Assistente → (Agendamentos / Notas / PDFs) → Banco de Dados

### Camadas
- Interface (CLI)
- Lógica (agendamentos, notas, PDFs)
- Banco de Dados SQLite
- Manipulação externa (arquivos, áudio)

## 🚀 Tecnologias e Ferramentas

- Python
- Bibliotecas: speech_recognition, pyttsx3, winsound, sqlite3, pdfplumber, colorama
- Manipulação de arquivos: os, shutil

## ⚙️ Como Executar

### Pré-requisitos
- Python 3.10+
- Pip instalado
- Microfone (para modo voz)

### Instalação
```bash
pip install speechrecognition pyttsx3 pdfplumber colorama
```

### Executar
```bash
python joelma.py
```

## 🧪 Testes
```bash
pytest
```

## 📚 Exemplos de Uso
- Criar agendamento
- Criar notas
- Baixar PDFs
- Alternar modo voz/digitação

## 💡 Roadmap
- Integração com WhatsApp, Telegram, Google Calendar
- Interface web
- Exportar notas para PDF
- Dashboard visual

## 🤝 Contribuição
1. Fork
2. Branch
3. Pull Request

## 📄 Licença
MIT
