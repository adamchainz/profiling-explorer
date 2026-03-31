class PePaginationMarker extends HTMLElement {
  connectedCallback() {
    this._observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          this._observer.disconnect();
          this._load();
        }
      },
      { root: document.querySelector('main'), rootMargin: '200px' }
    );
    this._observer.observe(this);
  }

  disconnectedCallback() {
    this._observer?.disconnect();
  }

  async _load() {
    const response = await fetch(this.dataset.url);
    const html = await response.text();
    const tmpl = document.createElement('template');
    tmpl.innerHTML = html;

    const tbody = document.querySelector('tbody');
    for (const row of tmpl.content.querySelectorAll('tr')) {
      tbody.appendChild(row);
    }

    const nextMarker = tmpl.content.querySelector('pe-pagination-marker');
    if (nextMarker) {
      this.replaceWith(nextMarker);
    } else {
      this.remove();
    }
  }
}

customElements.define('pe-pagination-marker', PePaginationMarker);

document.addEventListener('click', (e) => {
  const btn = e.target.closest('button.copy-btn');
  if (!btn) return;

  const text = btn.dataset.copy;
  navigator.clipboard.writeText(text).then(() => {
    btn.classList.add('copied');
    setTimeout(() => btn.classList.remove('copied'), 1500);
  });
});
