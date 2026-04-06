let services = [];

fetch('data/services.json')
  .then(r => r.json())
  .then(data => {
    services = data;
    render(services);
  });

function render(list) {
  const main = document.getElementById('services');
  if (list.length === 0) {
    main.innerHTML = '<p style="grid-column:1/-1;text-align:center;color:#888;padding:2rem;">No services found.</p>';
    return;
  }
  main.innerHTML = list.map(s => `
    <div class="card">
      <h2><a href="/cancel/${s.slug}/" style="color:inherit;text-decoration:none;">${s.name}</a></h2>
      <span class="difficulty d${s.cancel_difficulty}">${diffLabel(s.cancel_difficulty)}</span>
      <ol class="steps">${s.cancel_steps.map(step => `<li>${step}</li>`).join('')}</ol>
      ${s.known_friction ? `<div class="friction">Watch out: ${s.known_friction}</div>` : ''}
      ${s.cancel_url ? `<a class="cancel-btn" href="${s.cancel_url}" target="_blank" rel="noopener">Go to cancel page</a>` : ''}
    </div>
  `).join('');
}

function diffLabel(d) {
  return ['', 'Easy', 'Simple', 'Moderate', 'Difficult', 'Very Hard'][d] || 'Unknown';
}

document.getElementById('search').addEventListener('input', e => {
  const q = e.target.value.toLowerCase().trim();
  render(q ? services.filter(s =>
    s.name.toLowerCase().includes(q) ||
    s.category.toLowerCase().includes(q)
  ) : services);
});
