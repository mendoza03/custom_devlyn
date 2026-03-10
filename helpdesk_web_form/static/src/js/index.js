window.addEventListener('load', function () {

    const section = document.getElementById('section');
    const category = document.getElementById('category');
    const subcategory = document.getElementById('subcategory');
    const micasBlock = document.getElementById('micas-sin-cortar-block');

    if (!section || !category || !subcategory) return;

    // ✅ Ocultar bloque al inicio
    if (micasBlock) micasBlock.style.display = 'none';

    section.addEventListener('change', function () {
        const section_id = this.value;

        category.innerHTML = '<option value="">-- seleccionar --</option>';
        category.value = "";
        subcategory.innerHTML = '<option value="">-- seleccionar --</option>';
        subcategory.value = "";

        // ✅ Ocultar bloque al cambiar sección
        if (micasBlock) micasBlock.style.display = 'none';

        if (!section_id) return;

        category.disabled = true;

        fetch('/helpdesk/categories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ section_id })
        })
        .then(res => {
            if (!res.ok) throw new Error('Error del servidor');
            return res.json();
        })
        .then(data => {
            const frag = document.createDocumentFragment();
            data.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = c.name;
                frag.appendChild(opt);
            });
            category.appendChild(frag);
            category.disabled = false;
        })
        .catch(err => {
            console.error('Error cargando categorías:', err);
            category.disabled = false;
        });
    });

    category.addEventListener('change', function () {
        const category_id = this.value;

        subcategory.innerHTML = '<option value="">-- seleccionar --</option>';
        subcategory.value = "";

        // ✅ Ocultar bloque al cambiar categoría
        if (micasBlock) micasBlock.style.display = 'none';

        if (!category_id) return;

        subcategory.disabled = true;

        fetch('/helpdesk/subcategories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ category_id })
        })
        .then(res => {
            if (!res.ok) throw new Error('Error del servidor');
            return res.json();
        })
        .then(data => {
            const frag = document.createDocumentFragment();
            data.forEach(sc => {
                const opt = document.createElement('option');
                opt.value = sc.id;
                opt.textContent = sc.name;
                frag.appendChild(opt);
            });
            subcategory.appendChild(frag);
            subcategory.disabled = false;
        })
        .catch(err => {
            console.error('Error cargando subcategorías:', err);
            subcategory.disabled = false;
        });
    });

    subcategory.addEventListener('change', function () {
        const selectedText = this.options[this.selectedIndex]?.text?.trim();

        if (micasBlock) {
            micasBlock.style.display = (selectedText === 'Micas sin cortar') ? 'block' : 'none';
        }
    });

});
