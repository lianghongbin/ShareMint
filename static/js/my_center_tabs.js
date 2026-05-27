(function () {
    var root = document.querySelector('[data-my-center]');
    if (!root) return;

    var tabs = root.querySelectorAll('[data-my-tab]');
    var panels = root.querySelectorAll('[data-my-panel]');

    function showTab(name) {
        tabs.forEach(function (tab) {
            var active = tab.getAttribute('data-my-tab') === name;
            tab.classList.toggle('is-active', active);
            tab.setAttribute('aria-selected', active ? 'true' : 'false');
        });
        panels.forEach(function (panel) {
            var active = panel.getAttribute('data-my-panel') === name;
            panel.classList.toggle('is-active', active);
            panel.hidden = !active;
        });
    }

    tabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
            showTab(tab.getAttribute('data-my-tab'));
        });
    });

    var initial = new URLSearchParams(window.location.search).get('tab');
    if (initial === 'security' || initial === 'profile' || initial === 'system') {
        showTab(initial);
    }
})();
