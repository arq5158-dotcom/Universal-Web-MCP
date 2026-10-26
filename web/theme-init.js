// Applies the saved theme before the first paint (no white flash), same approach as the Ashzo app.
// Preference: 'light' | 'dark' | 'system' (default). The live switching lives in app.js.
(function () {
  var root = document.documentElement;
  try {
    var pref = localStorage.getItem('ashzo_theme');
    if (pref !== 'light' && pref !== 'dark') pref = 'system';
    var dark = pref === 'dark' || (pref === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
    root.setAttribute('data-theme', dark ? 'dark' : 'light');
    root.classList.toggle('dark', dark);
  } catch (e) {
    root.setAttribute('data-theme', 'dark');
    root.classList.add('dark');
  }
})();
