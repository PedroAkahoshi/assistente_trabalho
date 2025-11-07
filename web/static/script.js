let recognizing = false;
let recognition;

// Verifica se a API de reconhecimento de voz existe no navegador
if ('webkitSpeechRecognition' in window) {
    recognition = new webkitSpeechRecognition();
    recognition.lang = "pt-BR";
    recognition.continuous = true; // Mantém o reconhecimento ativo

    recognition.onresult = function(event) {
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
                let transcript = event.results[i][0].transcript.trim();
                // Remove pontuação final indesejada
                transcript = transcript.replace(/[?.!;]$/, "");
                sendVoiceMessage(transcript);
            }
        }
    };

    recognition.onend = function() {
        recognizing = false;
        document.getElementById("status").textContent = "Clique em 'Iniciar Voz' para falar.";
    };

    recognition.onerror = function(event) {
        console.error("Erro no reconhecimento de voz:", event.error);
        recognizing = false;
        document.getElementById("status").textContent = "Erro no reconhecimento.";
    };

} else {
    // Esconde os botões se a API não for suportada
    document.getElementById("start-voice").style.display = 'none';
    document.getElementById("stop-voice").style.display = 'none';
    document.getElementById("status").textContent = "Reconhecimento de voz não é suportado neste navegador.";
}

// --- Botão iniciar voz ---
document.getElementById("start-voice").onclick = () => {
    if (!recognizing && recognition) {
        recognition.start();
        recognizing = true;
        document.getElementById("status").textContent = "Assistente ouvindo...";
    }
};

// --- Botão parar voz ---
document.getElementById("stop-voice").onclick = () => {
    if (recognizing && recognition) {
        recognition.stop();
        recognizing = false;
        document.getElementById("status").textContent = "Assistente parou de ouvir.";
    }
};

// --- Enviar mensagem digitada ---
document.getElementById("message-form").addEventListener("submit", async function(event) {
    event.preventDefault();
    const input = document.getElementById("user-input");
    const message = input.value.trim();
    if (!message) return;

    appendMessage("Você: " + message, "user-message");
    input.value = ""; // Limpa o input imediatamente
    await getResponse(message);
});

// --- Enviar mensagem reconhecida por voz ---
async function sendVoiceMessage(message) {
    appendMessage("Você: " + message, "user-message");
    await getResponse(message);
}

// --- Buscar resposta do backend ---
async function getResponse(message) {
    try {
        const response = await fetch("/send_message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message })
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        appendMessage("Assistente: " + data.response, "ia-message");
    } catch (err) {
        console.error("Fetch Error:", err);
        appendMessage("Assistente: Desculpe, ocorreu um erro de conexão com o servidor.", "ia-message error");
    }
}

// --- Adicionar mensagem ao chat ---
function appendMessage(text, cls) {
    const chat = document.getElementById("chat");
    const div = document.createElement("div");
    div.className = "chat-message " + cls;
    
    // Converte quebras de linha (\n) em tags <br> para exibir corretamente no HTML
    div.innerHTML = text.replace(/\n/g, '<br>');

    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight; // Rola para a mensagem mais recente
}