(function () {
    var STORAGE_KEY = 'sharemint-ios-install-dismissed';
    var DISMISS_DAYS = 7;

    function isIOS() {
        return /iPad|iPhone|iPod/.test(navigator.userAgent)
            || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    }

    function isSafariIOS() {
        if (!isIOS()) return false;
        var ua = navigator.userAgent;
        return /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS|OPiOS|DuckDuckGo/.test(ua);
    }

    function isStandalone() {
        return window.matchMedia('(display-mode: standalone)').matches
            || window.navigator.standalone === true;
    }

    function isDismissedRecently() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return false;
            var ts = parseInt(raw, 10);
            if (Number.isNaN(ts)) return false;
            return Date.now() - ts < DISMISS_DAYS * 86400000;
        } catch (e) {
            return false;
        }
    }

    function dismiss() {
        var root = document.getElementById('ios-pwa-install');
        if (root) root.classList.add('hidden');
        try {
            localStorage.setItem(STORAGE_KEY, String(Date.now()));
        } catch (e) {}
    }

    function show() {
        var root = document.getElementById('ios-pwa-install');
        if (!root) return;
        root.classList.remove('hidden');
    }

    function init() {
        if (!isSafariIOS() || isStandalone() || isDismissedRecently()) return;
        window.setTimeout(show, 600);

        document.querySelectorAll('[data-ios-pwa-dismiss]').forEach(function (el) {
            el.addEventListener('click', dismiss);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
