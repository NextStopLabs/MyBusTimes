// public/js/tabs.js

function renderTabs(tabs) {
  return `
    <ul class="tabs">
      ${tabs
        .map(tab => {
          const isActive = tab.active ? 'active' : '';
          if (tab.active) {
            return `<li class="${isActive}">${tab.name}</li>`;
          } else {
            return `<li class="${isActive}"><a href="${tab.url}">${tab.name}</a></li>`;
          }
        })
        .join('')}
    </ul>
  `;
}
