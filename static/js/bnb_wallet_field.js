(function () {
    var LENGTH = 42;
    var PATTERN = /^0x[0-9a-fA-F]{40}$/;

    var LENGTH_ERROR =
        'BNB 链地址长度必须为 42 位（0x 开头 + 40 位十六进制）。' +
        '当前长度不正确，无法提交。填错链或填错地址将导致转入资金无法找回。';
    var FORMAT_ERROR =
        'BNB 链地址格式无效：必须以 0x 开头，且仅包含十六进制字符。' +
        '无法提交。填错链或填错地址将导致转入资金无法找回。';

    function validate(value) {
        var text = (value || '').trim();
        if (!text) {
            return 'BNB 钱包地址为必填项。';
        }
        if (text.length !== LENGTH) {
            return LENGTH_ERROR + '（当前 ' + text.length + ' 位，应为 ' + LENGTH + ' 位）';
        }
        if (!PATTERN.test(text)) {
            return FORMAT_ERROR;
        }
        return '';
    }

    function bindField(field) {
        var input = field.querySelector('[data-bnb-wallet-input]');
        var errorBox = field.querySelector('[data-bnb-wallet-error]');
        var counter = field.querySelector('[data-bnb-wallet-counter]');
        var form = field.closest('form');
        if (!input || !errorBox || !form) {
            return;
        }

        function setError(message) {
            if (message) {
                input.classList.add('is-invalid');
                input.setAttribute('aria-invalid', 'true');
                errorBox.textContent = message;
                errorBox.hidden = false;
            } else {
                input.classList.remove('is-invalid');
                input.removeAttribute('aria-invalid');
                errorBox.textContent = '';
                errorBox.hidden = true;
            }
        }

        function refresh() {
            var text = input.value.trim();
            if (counter) {
                counter.textContent = text.length + ' / ' + LENGTH + ' 位';
                counter.classList.toggle('is-valid', text.length === LENGTH && PATTERN.test(text));
                counter.classList.toggle('is-invalid', text.length > 0 && text.length !== LENGTH);
            }
            if (document.activeElement === input || input.classList.contains('is-invalid')) {
                setError(validate(text));
            }
        }

        input.addEventListener('input', function () {
            if (input.value.length > LENGTH) {
                input.value = input.value.slice(0, LENGTH);
            }
            refresh();
        });

        input.addEventListener('blur', function () {
            setError(validate(input.value));
        });

        form.addEventListener('submit', function (event) {
            var message = validate(input.value);
            if (message) {
                event.preventDefault();
                setError(message);
                input.focus();
            }
        });

        refresh();
    }

    function init() {
        document.querySelectorAll('[data-bnb-wallet-field]').forEach(bindField);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
