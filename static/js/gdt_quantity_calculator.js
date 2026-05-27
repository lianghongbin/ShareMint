(function () {
    function parseAmount(value) {
        var text = String(value || '').trim().replace(/,/g, '');
        if (!text) return null;
        var num = Number(text);
        if (!Number.isFinite(num) || num <= 0) return null;
        return num;
    }

    function parseFeePercent(value) {
        var text = String(value || '').trim().replace(/,/g, '');
        if (!text) return 0;
        var num = Number(text);
        if (!Number.isFinite(num) || num < 0) return null;
        return num;
    }

    function calcNetAmount(amount, feePercent) {
        if (!amount || feePercent == null) return null;
        if (feePercent >= 100) return null;
        return amount * (1 - feePercent / 100);
    }

    function calcGdtQuantity(amount, feePercent, price) {
        if (!price || price <= 0) return null;
        var net = calcNetAmount(amount, feePercent);
        if (net == null || net <= 0) return null;
        return Math.round(net / price);
    }

    function formatUsdt(value) {
        return value.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
    }

    function formatGdt(value) {
        if (value == null) return '—';
        return value.toLocaleString('zh-CN');
    }

    document.querySelectorAll('[data-gdt-calculator]').forEach(function (root) {
        var priceEl = root.querySelector('[data-gdt-price]');
        var amountInput = document.getElementById(root.dataset.amountInputId || 'investment_amount');
        var quantityInput = document.getElementById(root.dataset.quantityInputId || 'holding_quantity');
        var feeInput = root.querySelector('[data-gdt-fee]');
        var previewEl = root.querySelector('[data-gdt-preview]');
        var calcBtn = root.querySelector('[data-gdt-calc-btn]');

        if (!priceEl || !amountInput || !quantityInput || !feeInput) return;

        var price = Number(priceEl.textContent);
        if (!Number.isFinite(price) || price <= 0) return;

        function updatePreview() {
            var amount = parseAmount(amountInput.value);
            var feePercent = parseFeePercent(feeInput.value);
            if (!previewEl) return;

            if (amount == null) {
                previewEl.textContent = '请输入投资金额';
                return;
            }
            if (feePercent == null) {
                previewEl.textContent = '手续费比例不能为负数';
                return;
            }
            if (feePercent >= 100) {
                previewEl.textContent = '手续费比例须小于 100%';
                return;
            }

            var gdt = calcGdtQuantity(amount, feePercent, price);
            if (gdt == null) {
                previewEl.textContent = '扣除手续费后金额须大于 0';
                return;
            }

            if (feePercent > 0) {
                var feeAmount = amount * feePercent / 100;
                previewEl.textContent =
                    '扣除手续费 ' + feePercent + '%（' + formatUsdt(feeAmount) + ' USDT）后，可兑换约 ' +
                    formatGdt(gdt) + ' GDT';
                return;
            }
            previewEl.textContent = '按当前价格可兑换约 ' + formatGdt(gdt) + ' GDT';
        }

        function fillQuantity() {
            var amount = parseAmount(amountInput.value);
            var feePercent = parseFeePercent(feeInput.value);
            var gdt = calcGdtQuantity(amount, feePercent, price);
            if (gdt == null) {
                if (amount == null) {
                    amountInput.focus();
                } else if (feePercent == null || feePercent >= 100) {
                    feeInput.focus();
                } else {
                    amountInput.focus();
                }
                updatePreview();
                return;
            }
            quantityInput.value = String(gdt);
            updatePreview();
        }

        amountInput.addEventListener('input', updatePreview);
        amountInput.addEventListener('change', updatePreview);
        feeInput.addEventListener('input', updatePreview);
        feeInput.addEventListener('change', updatePreview);

        if (calcBtn) {
            calcBtn.addEventListener('click', fillQuantity);
        }

        updatePreview();
    });
})();
