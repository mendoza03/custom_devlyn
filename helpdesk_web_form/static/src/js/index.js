window.addEventListener('load', function () {

    const section = document.getElementById('section');
    const category = document.getElementById('category');
    const subcategory = document.getElementById('subcategory');

    if (!section || !category || !subcategory) return;

    section.addEventListener('change', function () {
        const section_id = this.value;

        category.innerHTML = '<option value="">-- seleccionar --</option>';
        subcategory.innerHTML = '<option value="">-- seleccionar --</option>';

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

        if (!category_id) return;

        fetch('/helpdesk/subcategories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ category_id })
        })
        .then(res => res.json())
        .then(data => {
            data.forEach(sc => {
                subcategory.innerHTML += `<option value="${sc.id}">${sc.name}</option>`;
            });
        });
    });

});