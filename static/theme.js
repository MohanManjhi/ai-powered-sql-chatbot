// Light/Dark mode toggle
const btn = document.getElementById('toggle-mode');
if (btn) {
  btn.onclick = function() {
    document.body.classList.toggle('dark-mode');
  }
}
