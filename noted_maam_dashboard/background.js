// Enable opening the side panel on extension icon click
chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch((error) => console.error(error));

// Listen for messages from the content script (e.g. when floating button is clicked)
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "open_side_panel" && sender.tab?.id) {
    chrome.sidePanel.open({ tabId: sender.tab.id })
      .then(() => sendResponse({ success: true }))
      .catch((error) => {
        console.error(error);
        sendResponse({ success: false, error: error.message });
      });
    return true; // Keep message channel open for async response
  }
});
