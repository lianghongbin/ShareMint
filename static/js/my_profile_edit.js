(function () {
    var form = document.querySelector('[data-my-profile-form]');
    if (!form) return;

    var block = form.querySelector('[data-my-profile-block]');
    var btnEdit = form.querySelector('[data-my-profile-edit]');
    var btnCancel = form.querySelector('[data-my-profile-cancel]');
    var inputs = form.querySelectorAll('.field-edit');
    var snapshot = {};
    var params = new URLSearchParams(window.location.search);
    var emailModal = document.getElementById('email-change-modal');

    function snapshotValues() {
        snapshot = {};
        inputs.forEach(function (inp) {
            if (inp.name) snapshot[inp.name] = inp.value;
        });
    }

    function restoreValues() {
        inputs.forEach(function (inp) {
            if (inp.name) inp.value = snapshot[inp.name] || '';
        });
    }

    function enterEdit() {
        snapshotValues();
        block.classList.add('is-editing');
        form.classList.add('is-editing');
    }

    function exitEdit() {
        restoreValues();
        block.classList.remove('is-editing');
        form.classList.remove('is-editing');
        closeEmailChangeModal();
    }

    function openEmailChangeModal(e) {
        if (e) e.preventDefault();
        if (!emailModal) return;
        emailModal.hidden = false;
    }

    function closeEmailChangeModal() {
        if (!emailModal) return;
        emailModal.hidden = true;
    }

    btnEdit.addEventListener('click', enterEdit);
    btnCancel.addEventListener('click', exitEdit);

    form.querySelectorAll('[data-email-change-open]').forEach(function (link) {
        link.addEventListener('click', openEmailChangeModal);
    });

    if (emailModal) {
        emailModal.addEventListener('click', function (e) {
            if (e.target.closest('[data-modal-close]')) closeEmailChangeModal();
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && !emailModal.hidden) closeEmailChangeModal();
        });
    }

    var center = document.querySelector('[data-my-center]');
    if (center) {
        center.querySelectorAll('[data-my-tab]').forEach(function (tab) {
            tab.addEventListener('click', function () {
                if (tab.getAttribute('data-my-tab') !== 'profile' && form.classList.contains('is-editing')) {
                    exitEdit();
                }
            });
        });
    }

    if (params.get('email_change') === '1') {
        openEmailChangeModal();
    }
})();
