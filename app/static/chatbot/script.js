function restartChat() {
    chatBox.innerHTML = "";
    userInput.value = "";
}

function sendMessage() {
    const prompt = userInput.value.trim();
    if (!prompt) return;

    addMessage(prompt, "user");
    userInput.value = "";
    addLoading();

    const evtSource = new EventSource(`/api/${challengeId}/generate_stream?prompt=${encodeURIComponent(prompt)}`);

    let botMsgDiv = document.createElement("div");
    botMsgDiv.classList.add("message", "bot-msg");
    chatBox.appendChild(botMsgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;

    let firstChunk = true;

    evtSource.onmessage = (e) => {
        try {
            const data = JSON.parse(e.data);
            if (firstChunk) {
                removeLoading();
                firstChunk = false;
            }
            botMsgDiv.innerText += data.text;
            chatBox.scrollTop = chatBox.scrollHeight;
        } catch (err) {
            console.error("Failed to parse SSE data:", err);
        }
    };

    evtSource.onerror = () => {
        removeLoading();
        evtSource.close();
    };
}

sendBtn.addEventListener("click", sendMessage);
userInput.addEventListener("keypress", e => {
    if (e.key === "Enter") sendMessage();
});
restartBtn.addEventListener("click", restartChat);