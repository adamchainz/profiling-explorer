async function fetchDoc(url, options) {
  const response = await fetch(url, options);
  const html = await response.text();
  return new DOMParser().parseFromString(html, 'text/html');
}

// Filter box
const searchInput = document.getElementById('pe-search');
let searchTimeout = null;
let searchAbort = null;

searchInput.addEventListener('input', () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(async () => {
    const q = searchInput.value.trim();
    const url = new URL(window.location.href);
    if (q) {
      url.searchParams.set('q', q);
    } else {
      url.searchParams.delete('q');
    }
    history.replaceState(null, '', url);

    searchAbort?.abort();
    searchAbort = new AbortController();
    try {
      const doc = await fetchDoc(url, { signal: searchAbort.signal });
      document.querySelector('main').replaceWith(doc.querySelector('main'));
    } catch (e) {
      if (e.name !== 'AbortError') throw e;
    }
  }, 300);
});

// Copy buttons
document.addEventListener('click', (e) => {
  const btn = e.target.closest('button.copy-btn');
  if (!btn) return;

  const text = btn.dataset.copy;
  navigator.clipboard.writeText(text).then(() => {
    btn.classList.add('copied');
    setTimeout(() => btn.classList.remove('copied'), 1500);
  });
});


// Pagination
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
    const doc = await fetchDoc(this.dataset.url);

    const tbody = document.querySelector('tbody');
    for (const row of doc.querySelectorAll('tbody tr')) {
      tbody.appendChild(document.adoptNode(row));
    }

    const nextMarker = doc.querySelector('pe-pagination-marker');
    if (nextMarker) {
      this.replaceWith(document.adoptNode(nextMarker));
    } else {
      this.remove();
    }
  }
}

customElements.define('pe-pagination-marker', PePaginationMarker);
