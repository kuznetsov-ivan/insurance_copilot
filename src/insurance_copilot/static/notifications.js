const notificationFeed = document.getElementById("notificationFeed");

function formatTimestamp(value) {
  return new Date(value).toLocaleString();
}

function renderNotifications(items) {
  if (!items.length) {
    notificationFeed.innerHTML = '<div class="detail-card empty">No notifications have been sent yet.</div>';
    return;
  }

  notificationFeed.innerHTML = items
    .map(
      (item) => `
        <article class="notification-card">
          <div class="headline-row">
            <span class="pill ${item.coverage_status}">${item.coverage_status.replace("_", " ")}</span>
            <strong>${item.customer_name || "Unknown customer"}</strong>
          </div>
          <p>${item.message}</p>
          <div class="meta-row">
            <span>${item.phone || "No phone on file"}</span>
            <span>${formatTimestamp(item.timestamp)}</span>
          </div>
        </article>
      `
    )
    .join("");
}

async function refreshNotifications() {
  const response = await fetch("/api/notifications");
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  const data = await response.json();
  renderNotifications(data.notifications);
}

refreshNotifications().catch((error) => {
  notificationFeed.innerHTML = `<div class="detail-card empty">Error: ${error.message}</div>`;
});
window.setInterval(() => {
  refreshNotifications().catch(() => {});
}, 5000);
