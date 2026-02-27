window.addEventListener('load', function () {

    const section = document.getElementById('section');
    const category = document.getElementById('category');
    const subcategory = document.getElementById('subcategory');

    if (!section || !category || !subcategory) return;

    function _qs(selector) {
        return document.querySelector(selector);
    }

    function _allBlocks() {
        return Array.from(document.querySelectorAll('[id^="blk_"]'));
    }

    function _hideAllBlocks() {
        _allBlocks().forEach(el => el.classList.add('d-none'));
    }

    function _normalizeCode(code) {
        return (code || '').toString().trim().toLowerCase();
    }

    function _showBlockByCode(code) {
        const c = _normalizeCode(code);
        if (!c) return;
        const el = document.getElementById(`blk_${c}`);
        if (el) el.classList.remove('d-none');
    }

    function _getSelectedSubcategoryId() {
        return (subcategory.value || '').toString().trim();
    }

    function _getSelectedSubcategoryCodeFromOption() {
        const opt = subcategory.options[subcategory.selectedIndex];
        if (!opt) return '';
        return _normalizeCode(opt.getAttribute('data-code'));
    }

    function _getVisibleSelectByName(name) {
        const els = Array.from(document.querySelectorAll(`select[name="${name}"]`));
        return els.find(el => !el.closest('.d-none')) || els[0] || null;
    }

    function _updateSatisfaccionBlocks() {
        const orderTypeEl = _getVisibleSelectByName('x_order_type');
        const val = orderTypeEl ? (orderTypeEl.value || '') : '';

        const blkAdapt = document.getElementById('blk_satisfaccion_adaptacion');
        const blkImg = document.getElementById('blk_satisfaccion_imagen');

        if (blkAdapt) blkAdapt.classList.add('d-none');
        if (blkImg) blkImg.classList.add('d-none');

        if (val === 'satisfaccion_adaptacion' && blkAdapt) blkAdapt.classList.remove('d-none');
        if (val === 'satisfaccion_imagen' && blkImg) blkImg.classList.remove('d-none');
    }

    function _updateTonerWarn() {
        const tonerEl = document.getElementById('x_toner_below_15') || _qs('select[name="x_toner_below_15"]');
        const warnEl = document.getElementById('toner_no_warn');
        if (!tonerEl || !warnEl) return;

        if ((tonerEl.value || '') === 'no') warnEl.classList.remove('d-none');
        else warnEl.classList.add('d-none');
    }

    function _bindDynamicListeners() {
        const orderTypeEl = _getVisibleSelectByName('x_order_type');
        if (orderTypeEl && !orderTypeEl.dataset.bound) {
            orderTypeEl.addEventListener('change', _updateSatisfaccionBlocks);
            orderTypeEl.dataset.bound = '1';
        }

        const tonerEl = document.getElementById('x_toner_below_15') || _qs('select[name="x_toner_below_15"]');
        if (tonerEl && !tonerEl.dataset.bound) {
            tonerEl.addEventListener('change', _updateTonerWarn);
            tonerEl.dataset.bound = '1';
        }
    }

    function _applyFrontVisibilityByCode(code) {
        _hideAllBlocks();
        _showBlockByCode(code);
        _updateSatisfaccionBlocks();
        _updateTonerWarn();
        _bindDynamicListeners();
    }

    function _applyFrontVisibilityFromSelection() {
        const codeFromOpt = _getSelectedSubcategoryCodeFromOption();
        if (codeFromOpt) {
            _applyFrontVisibilityByCode(codeFromOpt);
            return;
        }

        const subcategory_id = _getSelectedSubcategoryId();
        if (!subcategory_id) {
            _hideAllBlocks();
            return;
        }

        fetch('/helpdesk/subcategory_info', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ subcategory_id })
        })
            .then(res => res.json())
            .then(info => {
                const realCode = _normalizeCode(info && info.code);
                const opt = subcategory.options[subcategory.selectedIndex];
                if (opt && realCode) opt.setAttribute('data-code', realCode);
                _applyFrontVisibilityByCode(realCode);
            });
    }

    section.addEventListener('change', function () {
        const section_id = this.value;

        category.innerHTML = '<option value="">-- seleccionar --</option>';
        subcategory.innerHTML = '<option value="">-- seleccionar --</option>';
        _hideAllBlocks();

        if (!section_id) return;

        fetch('/helpdesk/categories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ section_id })
        })
            .then(res => res.json())
            .then(data => {
                data.forEach(c => {
                    category.innerHTML += `<option value="${c.id}">${c.name}</option>`;
                });
            });
    });

    category.addEventListener('change', function () {
        const category_id = this.value;

        subcategory.innerHTML = '<option value="">-- seleccionar --</option>';
        _hideAllBlocks();

        if (!category_id) return;

        fetch('/helpdesk/subcategories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ category_id })
        })
            .then(res => res.json())
            .then(data => {
                data.forEach(sc => {
                    const code = _normalizeCode(sc.code);
                    subcategory.innerHTML += `<option value="${sc.id}" data-code="${code}">${sc.name}</option>`;
                });
            });
    });

    subcategory.addEventListener('change', _applyFrontVisibilityFromSelection);

    _hideAllBlocks();
    _applyFrontVisibilityFromSelection();
});