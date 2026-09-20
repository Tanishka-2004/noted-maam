function injectButton() {
  if (document.getElementById("noted-maam-injected-trigger")) return;
  if (!document.body) {
    setTimeout(injectButton, 100);
    return;
  }

  const trigger = document.createElement("div");
  trigger.id = "noted-maam-injected-trigger";
  
  // Style the floating button (Pantone White & Olive Green Theme)
  trigger.style.position = "fixed";
  trigger.style.bottom = "80px";
  trigger.style.right = "24px";
  trigger.style.zIndex = "99999";
  trigger.style.display = "flex";
  trigger.style.alignItems = "center";
  trigger.style.gap = "8px";
  trigger.style.backgroundColor = "#FFFAFA"; // Snow White
  trigger.style.border = "1px solid rgba(107, 143, 59, 0.2)";
  trigger.style.borderRadius = "12px";
  trigger.style.padding = "10px 16px";
  trigger.style.boxShadow = "0 8px 30px rgba(0, 0, 0, 0.12)";
  trigger.style.cursor = "pointer";
  trigger.style.fontFamily = "'Plus Jakarta Sans', system-ui, sans-serif";
  trigger.style.transition = "all 0.3s cubic-bezier(0.16, 1, 0.3, 1)";
  
  // Custom Hover Effects
  trigger.addEventListener("mouseenter", () => {
    trigger.style.transform = "translateY(-4px)";
    trigger.style.boxShadow = "0 12px 35px rgba(107, 143, 59, 0.15)";
    trigger.style.borderColor = "rgba(107, 143, 59, 0.4)";
  });
  
  trigger.addEventListener("mouseleave", () => {
    trigger.style.transform = "translateY(0)";
    trigger.style.boxShadow = "0 8px 30px rgba(0, 0, 0, 0.12)";
    trigger.style.borderColor = "rgba(107, 143, 59, 0.2)";
  });

  // Inner elements (Branding + Label)
  trigger.innerHTML = `
    <div style="
      width: 24px;
      height: 24px;
      border-radius: 6px;
      background: linear-gradient(135deg, #6B8F3B, #527A2D);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      color: white;
      font-size: 10px;
      box-shadow: 0 0 10px rgba(107, 143, 59, 0.3);
    ">NM</div>
    <span style="
      font-size: 12px;
      font-weight: 700;
      color: #1a1a2e;
    ">Open Noted Ma'am</span>
  `;

  // Add click handler to request side panel opening
  trigger.style.userSelect = "none";
  trigger.addEventListener("click", () => {
    chrome.runtime.sendMessage({ action: "open_side_panel" }, (response) => {
      if (chrome.runtime.lastError) {
        console.warn("Could not open side panel natively; open the extension from your browser toolbar.");
        showFallbackNotification();
      }
    });
  });

  document.body.appendChild(trigger);
}

function showFallbackNotification() {
  const notification = document.createElement("div");
  notification.style.position = "fixed";
  notification.style.bottom = "140px";
  notification.style.right = "24px";
  notification.style.zIndex = "99999";
  notification.style.backgroundColor = "#1a1a2e";
  notification.style.color = "white";
  notification.style.padding = "8px 12px";
  notification.style.borderRadius = "8px";
  notification.style.fontSize = "11px";
  notification.style.fontFamily = "sans-serif";
  notification.style.boxShadow = "0 4px 15px rgba(0,0,0,0.2)";
  notification.innerText = "Please click the extension icon in your browser toolbar to open the sidebar.";
  document.body.appendChild(notification);
  setTimeout(() => notification.remove(), 4000);
}

// Run injection safely
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", injectButton);
} else {
  injectButton();
}
