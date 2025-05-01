// Config - Replace with your backend URL
const API_BASE_URL = "https://your-api-url.onrender.com";
let currentConnectionId = null;

// --- UI Helpers ---
function showLoading(elementId) {
    document.getElementById(elementId).innerHTML = `<div class="spinner">⌛ Loading...</div>`;
}

function showError(elementId, message) {
    const element = document.getElementById(elementId);
    element.innerHTML = `<span style="color:red">❌ ${message}</span>`;
    element.style.color = "red";
}

// --- Core Functions ---
async function pingIp() {
    const ip = document.getElementById("ping-ip").value.trim();
    if (!ip) return alert("Please enter an IP");
    
    showLoading("ping-result");
    try {
        const response = await fetch(`${API_BASE_URL}/ping?ip=${encodeURIComponent(ip)}`);
        const data = await response.json();
        const resultElement = document.getElementById("ping-result");
        resultElement.textContent = data.output;
        resultElement.style.color = data.success ? "green" : "red";
    } catch (error) {
        showError("ping-result", `API error: ${error.message}`);
    }
}

async function connectMikrotik() {
    const ip = document.getElementById("mkt-ip").value.trim();
    const port = document.getElementById("mkt-port").value || 8728;
    const username = document.getElementById("mkt-user").value.trim();
    const password = document.getElementById("mkt-pass").value;

    if (!ip || !username || !password) {
        return showError("mkt-status", "All fields are required!");
    }

    showLoading("mkt-status");
    try {
        const response = await fetch(`${API_BASE_URL}/connect`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ip, port, username, password })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Connection failed");
        }

        const data = await response.json();
        currentConnectionId = data.connection_id;
        document.getElementById("mkt-status").innerHTML = `<span style="color:green">✅ Connected to ${ip}</span>`;
        document.getElementById("fetch-info-btn").disabled = false;
    } catch (error) {
        showError("mkt-status", error.message);
    }
}

async function fetchSystemInfo() {
    if (!currentConnectionId) return;
    
    showLoading("system-info");
    try {
        const response = await fetch(
            `${API_BASE_URL}/system-info?connection_id=${encodeURIComponent(currentConnectionId)}`
        );
        const data = await response.json();
        
        const infoHtml = `
            <strong>Device:</strong> ${data.identity || "N/A"}<br>
            <strong>OS Version:</strong> ${data.version}<br>
            <strong>Board:</strong> ${data.board}<br>
            <strong>CPU Load:</strong> ${data.cpu}%<br>
            <strong>Memory:</strong> ${data.memory}<br>
            <strong>Uptime:</strong> ${data.uptime}
        `;
        document.getElementById("system-info").innerHTML = infoHtml;
    } catch (error) {
        showError("system-info", error.message);
    }
}