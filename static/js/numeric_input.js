(function () {
    function shouldSkip(input) {
        if (input.dataset.numericSkip !== undefined) return true;
        if (input.autocomplete === 'one-time-code') return true;
        var pattern = input.getAttribute('pattern') || '';
        if (input.maxLength === 6 && pattern.indexOf('[0-9]{6}') !== -1) return true;
        return false;
    }

    function isZeroPlaceholder(value) {
        var text = String(value || '').trim();
        if (text === '') return false;
        return /^0+(\.0*)?$/.test(text);
    }

    function isDecimalInput(input) {
        return input.getAttribute('inputmode') === 'decimal'
            || input.dataset.numericType === 'decimal'
            || input.classList.contains('input-numeric-decimal');
    }

    function normalizeValue(value, decimal) {
        if (!value) return value;

        var sign = '';
        if (value.charAt(0) === '-') {
            sign = '-';
            value = value.slice(1);
        }

        if (decimal) {
            var dotIndex = value.indexOf('.');
            var intPart = dotIndex >= 0 ? value.slice(0, dotIndex) : value;
            var fracPart = dotIndex >= 0 ? value.slice(dotIndex) : '';

            if (intPart === '') {
                intPart = '0';
            } else if (intPart.length > 1) {
                intPart = intPart.replace(/^0+(?=\d)/, '');
            }

            return sign + intPart + fracPart;
        }

        if (/^0+$/.test(value)) return '0';
        return sign + value.replace(/^0+(?=\d)/, '');
    }

    function bindNumericInput(input) {
        if (!input || input.dataset.numericBound === '1' || shouldSkip(input)) return;
        input.dataset.numericBound = '1';

        var decimal = isDecimalInput(input);

        input.addEventListener('focus', function () {
            if (isZeroPlaceholder(this.value)) {
                this.value = '';
            }
        });

        input.addEventListener('keydown', function (e) {
            if (e.key.length !== 1 || !/\d/.test(e.key)) return;
            if (this.value !== '0') return;
            if (this.selectionStart !== this.selectionEnd) return;
            this.value = '';
        });

        input.addEventListener('input', function () {
            var value = this.value;
            if (!value) return;
            var normalized = normalizeValue(value, decimal);
            if (normalized !== value) {
                this.value = normalized;
            }
        });
    }

    function initNumericInputs(root) {
        (root || document).querySelectorAll(
            'input[inputmode="decimal"], input[inputmode="numeric"], input.input-numeric'
        ).forEach(bindNumericInput);
    }

    window.ShareMint = window.ShareMint || {};
    window.ShareMint.bindNumericInput = bindNumericInput;
    window.ShareMint.initNumericInputs = initNumericInputs;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            initNumericInputs();
        });
    } else {
        initNumericInputs();
    }
})();
