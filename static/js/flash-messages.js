(function () {
    var DURATION = 3000;

    function dismiss(el) {
        if (el.classList.contains('is-leaving')) return;
        el.classList.add('is-leaving');
        window.setTimeout(function () {
            el.remove();
        }, 320);
    }

    function initFlash(el) {
        if (el.dataset.flashReady) return;
        el.dataset.flashReady = '1';

        var timer = window.setTimeout(function () {
            dismiss(el);
        }, DURATION);

        var closeBtn = el.querySelector('.flash-message__close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function () {
                window.clearTimeout(timer);
                dismiss(el);
            });
        }
    }

    document.querySelectorAll('.flash-message').forEach(initFlash);
})();
