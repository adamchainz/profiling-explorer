document.addEventListener('click', (e) => {
  const btn = e.target.closest('button.copy-btn');
  if (!btn) return;

  const text = btn.dataset.copy;
  navigator.clipboard.writeText(text).then(() => {
    btn.classList.add('copied');
    setTimeout(() => btn.classList.remove('copied'), 1500);
  });
});
