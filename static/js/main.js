(function () {
    // Legacy top nav (auth fallback)
    const navToggle = document.querySelector('[data-nav-toggle]');
    const siteNav = document.querySelector('[data-site-nav]');
    if (navToggle && siteNav) {
        navToggle.addEventListener('click', function () {
            const isOpen = siteNav.classList.toggle('is-open');
            navToggle.setAttribute('aria-expanded', String(isOpen));
        });
    }

    // App sidebar
    const sidebar = document.querySelector('[data-sidebar]');
    const sidebarToggle = document.querySelector('[data-sidebar-toggle]');
    const overlay = document.querySelector('[data-sidebar-overlay]');

    function closeSidebar() {
        if (!sidebar) return;
        sidebar.classList.remove('is-open');
        overlay?.classList.remove('is-visible');
    }

    function openSidebar() {
        if (!sidebar) return;
        sidebar.classList.add('is-open');
        overlay?.classList.add('is-visible');
    }

    sidebarToggle?.addEventListener('click', function () {
        if (sidebar?.classList.contains('is-open')) {
            closeSidebar();
        } else {
            openSidebar();
        }
    });

    overlay?.addEventListener('click', closeSidebar);

    window.addEventListener('resize', function () {
        if (window.innerWidth >= 1024) {
            closeSidebar();
        }
        siteNav?.classList.remove('is-open');
        navToggle?.setAttribute('aria-expanded', 'false');
    });

    // POST 表单：回车 / 手机键盘「前往」提交
    function isEnterEvent(e) {
        return e.key === 'Enter' || e.code === 'Enter' || e.code === 'NumpadEnter' || e.keyCode === 13;
    }

    function triggerFormSubmit(form) {
        var submitControl = form.querySelector(
            'input[type="submit"].btn-primary, button[type="submit"].btn-primary, ' +
            'input[type="submit"]:not(.btn-secondary):not(.btn-outline):not(.btn-ghost), ' +
            'button[type="submit"]:not(.btn-secondary):not(.btn-outline):not(.btn-ghost)'
        );
        if (submitControl && !submitControl.disabled) {
            submitControl.click();
            return;
        }
        if (typeof form.requestSubmit === 'function') {
            form.requestSubmit();
            return;
        }
        form.submit();
    }

    document.querySelectorAll('form.form-stack[method="post"]:not([data-no-enter-submit])').forEach(function (form) {
        var lastEnterAt = 0;
        function onEnter(e) {
            if (!isEnterEvent(e) || e.isComposing || e.shiftKey || e.altKey || e.ctrlKey || e.metaKey) {
                return;
            }
            var target = e.target;
            if (!target || target.tagName === 'TEXTAREA' || target.tagName === 'BUTTON') {
                return;
            }
            if (target.tagName === 'A' || target.closest('a')) {
                return;
            }
            if (target.type === 'submit' || target.type === 'button') {
                return;
            }

            var now = Date.now();
            if (now - lastEnterAt < 400) {
                return;
            }
            lastEnterAt = now;

            e.preventDefault();
            triggerFormSubmit(form);
        }
        form.addEventListener('keydown', onEnter);
        form.addEventListener('keyup', onEnter);
    });
})();
