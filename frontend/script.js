// DOM Elements
const inputText = document.getElementById("input-text");
const sendButton = document.getElementById("send-button");
const messagesDiv = document.getElementById("messages");
const newChatButton = document.getElementById("new-chat-btn");

// Welcome message and suggestion chips
const suggestionChips = [
  "Good restaurant with live music?",
  "Modify my reservation",
  "Cancel my reservation",
];

// Show welcome message
function showWelcomeMessage() {
  messagesDiv.innerHTML = `
    <div class="message welcome">
      <h1 class="welcome-title">Welcome to FoodieSpot Reservations</h1>
      <p class="welcome-subtitle">I'm your virtual reservation assistant. How can I help you today?</p>
      <div class="suggestion-chips">
        ${suggestionChips
          .map((chip) => `<div class="suggestion-chip">${chip}</div>`)
          .join("")}
      </div>
    </div>
  `;

  // Add event listeners to suggestion chips
  document.querySelectorAll(".suggestion-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      inputText.value = chip.textContent;
      inputText.focus();
      checkInput();
    });
  });
}

// Show welcome message on load
showWelcomeMessage();

// Adjust textarea height automatically
inputText.addEventListener("input", function () {
  this.style.height = "auto";
  this.style.height =
    (this.scrollHeight < 150 ? this.scrollHeight : 150) + "px";
  checkInput();
});

// Reset chat and clear message history on backend
newChatButton.addEventListener("click", async () => {
  try {
    // Call the new endpoint to reset conversation history
    const response = await fetch("http://localhost:8000/reset_chat", {
      method: "POST",
    });

    if (!response.ok) {
      console.error("Error resetting chat:", response.statusText);
    }
  } catch (error) {
    console.error("Failed to reset chat history:", error);
  }

  // Reset UI
  showWelcomeMessage();
  inputText.value = "";
  inputText.style.height = "auto";
  sendButton.disabled = true;
});

// Check if input has text to enable/disable send button
function checkInput() {
  sendButton.disabled = inputText.value.trim() === "";
}

// Handle pressing Enter to send message
inputText.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    if (!sendButton.disabled) {
      sendButton.click();
    }
  }
});

// Format message with avatar and sender info
function formatMessage(role, content) {
  const isUser = role === "user";
  const avatar = isUser
    ? '<i class="fas fa-user"></i>'
    : '<i class="fas fa-robot"></i>';
  const sender = isUser ? "You" : "Assistant";

  return `
    <div class="message ${role} clearfix">
      <div class="message-info">
        ${
          isUser
            ? ""
            : `
          <div class="message-avatar">
            ${avatar}
          </div>
        `
        }
        ${
          isUser
            ? `
          <div class="message-sender">
            ${sender}
          </div>
        `
            : `
          <div class="message-sender">
            ${sender}
          </div>
        `
        }
        ${
          isUser
            ? `
          <div class="message-avatar">
            ${avatar}
          </div>
        `
            : ""
        }
      </div>
      <div class="message-content">
        ${content}
      </div>
    </div>
  `;
}

// Add message to chat
function appendMessage(role, text) {
  if (messagesDiv.querySelector(".welcome")) {
    messagesDiv.innerHTML = "";
  }

  const formattedContent =
    role === "assistant" && text ? marked.parse(text) : text;
  const messageHTML = formatMessage(role, formattedContent);

  const tempDiv = document.createElement("div");
  tempDiv.innerHTML = messageHTML;
  const messageEl = tempDiv.firstElementChild;

  messagesDiv.appendChild(messageEl);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;

  return messageEl.querySelector(".message-content");
}

// Add typing indicator
function showTypingIndicator() {
  const typingIndicator = document.createElement("div");
  typingIndicator.className = "message assistant clearfix typing";
  typingIndicator.innerHTML = `
    <div class="message-info">
      <div class="message-avatar">
        <i class="fas fa-robot"></i>
      </div>
      <div class="message-sender">
        Assistant
      </div>
    </div>
    <div class="message-content">
      <div class="typing-indicator">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>
  `;

  messagesDiv.appendChild(typingIndicator);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
  return typingIndicator;
}

// Remove typing indicator
function removeTypingIndicator() {
  const typingIndicator = messagesDiv.querySelector(".typing");
  if (typingIndicator) {
    typingIndicator.remove();
  }
}

// Send message to backend
sendButton.onclick = async () => {
  const message = inputText.value.trim();
  if (!message) return;

  // Add user message to chat
  appendMessage("user", message);

  // Clear input and resize
  inputText.value = "";
  inputText.style.height = "auto";
  sendButton.disabled = true;

  // Show typing indicator
  const typingIndicator = showTypingIndicator();

  try {
    const response = await fetch("http://localhost:8000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }

    // Remove typing indicator
    removeTypingIndicator();

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let assistantMsg = "";
    const el = appendMessage("assistant", "");

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value);
      assistantMsg += chunk;
      el.innerHTML = marked.parse(assistantMsg);
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
  } catch (error) {
    console.error("Error:", error);
    removeTypingIndicator();
    appendMessage(
      "assistant",
      "I'm having trouble connecting to the server. Please try again later."
    );
  }

  sendButton.disabled = false;
};

// Initialize
inputText.focus();
checkInput();
