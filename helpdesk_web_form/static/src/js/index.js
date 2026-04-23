window.addEventListener('load', function () {

    const form        = document.querySelector('form[action="/helpdesk/submit"]');
    const restoreNode = document.getElementById('helpdesk-form-data');
    const section     = document.getElementById('section');
    const category    = document.getElementById('category');
    const subcategory = document.getElementById('subcategory');
    let restoredData = {};

    try {
        if (restoreNode?.value) {
            restoredData = JSON.parse(atob(restoreNode.value));
        }
    } catch (error) {
        console.warn('Helpdesk form restore failed', error);
    }

    if (!form || !section || !category || !subcategory) return;

    const BLOCK_MAP = {
        'micas_sin_cortar':                        'block-micas_sin_cortar',
        'trabajos_atrasados':                      'block-trabajos_atrasados',
        'correo_electronico':                      'block-correo_electronico',
        'equipo_computo':                          'block-equipo_computo',
        'interredes':                              'block-interredes',
        'problemas_impresora':                     'block-problemas_impresora',
        'surtido_toner':                           'block-surtido_toner',
        'iluminacion':                             'block-iluminacion',
        'sanitarios':                              'block-sanitarios',
        'mobiliario':                              'block-mobiliario',
        'aparadores':                              'block-aparadores',
        'fletes':                                  'block-fletes',
        'limpieza_profunda':                       'block-limpieza_profunda',
        'no_recibidos_facturacion':                'block-no_recibidos_facturacion',
        'optica_digital':                          'block-optica_digital',
        'acceso_plataforma':                       'block-acceso_plataforma',
        'desbloqueo_usuario_contrasena':           'block-desbloqueo_usuario_contrasena',
        'aclaracion_saldo_vacaciones':             'block-aclaracion_saldo_vacaciones',
        'error_plataforma':                        'block-error_plataforma',
        'display_campanas_aperturas':              'block-display_campanas_aperturas',
        'reposicion_elemento_danado':              'block-reposicion_elemento_danado',
        'apoyo_aplicar_convenio':                  'block-apoyo_aplicar_convenio',
        'convenios_institucionales':               'block-convenios_institucionales',
        'no_entran_manuales':                      'block-no_entran_manuales',
        'dudas_promociones':                       'block-dudas_promociones',
        'problema_pagos_anticipos':                'block-problema_pagos_anticipos',
        'captura_ov':                              'block-captura_ov',
        'cierre_diario':                           'block-cierre_diario',
        'no_recepcionar_bolsa':                    'block-no_recepcionar_bolsa',
        'pedido_sin_embalaje':                     'block-pedido_sin_embalaje',
        'problema_captura_devolucion':             'block-problema_captura_devolucion',
        'rescate_cancelaciones_clientes_molestos': 'block-rescate_cancelaciones_clientes_molestos',
        'pedidos_incompletos':                     'block-pedidos_incompletos',
        'graduacion_incorrecta':                   'block-graduacion_incorrecta',
        'pedido_otro_cliente':                     'block-pedido_otro_cliente',
        'devolucion_pedidos':                      'block-devolucion_pedidos',
        'graduacion_error_cliente':                'block-graduacion_error_cliente',
        'pedidos_sin_estatus':                     'block-pedidos_sin_estatus',
        'paquete_retornado':                       'block-paquete_retornado',
        'cambio_domicilio':                        'block-cambio_domicilio',
        'pedido_sin_capturar':                     'block-pedido_sin_capturar',
        'graduacion_sucursal':                     'block-graduacion_sucursal',
        'devolucion_sin_entregar':                 'block-devolucion_sin_entregar',
        'pedido_sin_envio':                        'block-pedido_sin_envio',
        'atraso_lente_contacto':                   'block-atraso_lente_contacto',
        'busqueda_armazon':                        'block-busqueda_armazon',
        'calidad_micas':                           'block-calidad_micas',
        'calidad_armazon':                         'block-calidad_armazon',
        'implantar_bolsa':                         'block-implantar_bolsa',
        'bolsa_abasto_no_implantada':              'block-bolsa_abasto_no_implantada',
        'incumplimiento_visita':                   'block-incumplimiento_visita',
        'paquetes_alterados':                      'block-paquetes_alterados',
        'paquetes_no_recibidos_trabajo':           'block-paquetes_no_recibidos_trabajo',
        'paquetes_no_recibidos_abasto':            'block-paquetes_no_recibidos_abasto',
        'seguimiento_laboratorio':                 'block-seguimiento_laboratorio',
        'envio_extraordinario':                    'block-envio_extraordinario',
        'faltante_accesorios_pedido':              'block-faltante_accesorios_pedido',
        'faltante_accesorios_surtido':             'block-faltante_accesorios_surtido',
        'faltante_mercancia':                      'block-faltante_mercancia',
        'sobrante_mercancia':                      'block-sobrante_mercancia',
        'mercancia_danada':                        'block-mercancia_danada',
        'extravio_mensajeria':                     'block-extravio_mensajeria',
        'extravio_sucursal':                       'block-extravio_sucursal',
        'ale_pagina_web':                          'block-ale_pagina_web',
        'universidad_devlyn':                      'block-universidad_devlyn',
        'pagina_evaluaciones_productos':           'block-pagina_evaluaciones_productos',
        'pagina_evaluaciones_politicas':           'block-pagina_evaluaciones_politicas',
        'promocion_puesto':                        'block-promocion_puesto',

        // NUEVOS
        'seguimiento_solicitud':                   'block-seguimiento_solicitud',
        'trabajos_atrasados_laboratorio_local':    'block-trabajos_atrasados_laboratorio_local',
        'abasto_accesorios_soluciones':            'block-abasto_accesorios_soluciones',
        'abasto_armazones':                        'block-abasto_armazones',
        'devoluciones_aplicadas':                  'block-devoluciones_aplicadas',
        'gotas_soluciones_alcon':                  'block-gotas_soluciones_alcon',
    };

    const REFACTURACION_CODES = [
        'error_captura_datos_fiscales',
        'error_captura_uso_cfdi',
        'error_captura_forma_pago',
        'unificar_pedidos',
        'dividir_pedido',
        'unificar_conceptos',
        'diferencia_convenio_credito',
        'facturar_monto_especifico',
        'periodo_facturacion_portal',
    ];

    const DEV_REAL_TC_DB_CODES = ['cargos_duplicados', 'error_examen', 'fecha_entrega', 'mal_servicio'];
    const DEV_REAL_CASH_ORDER_CODES = ['error_examen', 'fecha_entrega', 'mal_servicio'];
    const DEV_REAL_CASH_TRANSFER_CODES = ['error_examen', 'fecha_entrega', 'mal_servicio'];

    const DEV_TC_EXTRA_BLOCKS = {
        'cargos_duplicados': 'block-dev-tc-cargos_duplicados',
        'error_examen':      'block-dev-tc-error_examen',
        'fecha_entrega':     'block-dev-tc-fecha_entrega',
    };
    const DEV_CASH_ORDER_EXTRA_BLOCKS = {
        'error_examen':  'block-dev-cash-order-error_examen',
        'fecha_entrega': 'block-dev-cash-order-fecha_entrega',
    };
    const DEV_CASH_TRANSFER_EXTRA_BLOCKS = {
        'error_examen':  'block-dev-cash-transfer-error_examen',
        'fecha_entrega': 'block-dev-cash-transfer-fecha_entrega',
    };

    const CONVENIOS_CODES = ['apoyo_aplicar_convenio', 'convenios_institucionales', 'no_entran_manuales', 'dudas_promociones'];

    let subcategoryCodes = {};
    let currentCategorySlug = '';

    function isVisible(el) {
        return Boolean(el) && el.offsetParent !== null;
    }

    function getDynamicFields() {
        return form.querySelectorAll(
            '.subcategory-block input, .subcategory-block select, .subcategory-block textarea,' +
            '#block-satisfaccion_adaptacion input, #block-satisfaccion_adaptacion select, #block-satisfaccion_adaptacion textarea,' +
            '#block-satisfaccion_imagen input, #block-satisfaccion_imagen select, #block-satisfaccion_imagen textarea'
        );
    }

    function clearDynamicRequired() {
        getDynamicFields().forEach(field => {
            field.required = false;
            field.setCustomValidity('');
        });
    }

    function applyRadioRequired(fields) {
        const radioNames = new Set();
        fields.forEach(field => {
            if (field.type === 'radio' && field.name) {
                radioNames.add(field.name);
            }
        });
        radioNames.forEach(name => {
            const visibleGroup = Array.from(
                form.querySelectorAll(`input[type="radio"][name="${CSS.escape(name)}"]`)
            ).filter(isVisible);
            visibleGroup.forEach(radio => {
                radio.required = false;
                radio.setCustomValidity('');
            });
            if (visibleGroup.length) {
                visibleGroup[0].required = true;
            }
        });
    }

    function syncDynamicRequired() {
        clearDynamicRequired();

        const visibleFields = Array.from(getDynamicFields()).filter(field => {
            if (!isVisible(field) || field.disabled) return false;
            if (field.type === 'hidden' || field.type === 'file') return false;
            return true;
        });

        visibleFields.forEach(field => {
            if (field.type !== 'radio' && field.type !== 'checkbox') {
                field.required = true;
            }
            field.setCustomValidity('');
        });

        applyRadioRequired(visibleFields);
    }

    function validateDynamicFields() {
        syncDynamicRequired();

        let firstInvalidField = null;
        const visibleFields = Array.from(getDynamicFields()).filter(field => {
            if (!isVisible(field) || field.disabled) return false;
            if (field.type === 'hidden' || field.type === 'file') return false;
            return true;
        });

        visibleFields.forEach(field => {
            field.setCustomValidity('');

            if (field.tagName === 'SELECT' && field.value === 'select') {
                field.setCustomValidity('Selecciona una opcion valida.');
            }

            if (!firstInvalidField && !field.checkValidity()) {
                firstInvalidField = field;
            }
        });

        if (firstInvalidField) {
            firstInvalidField.reportValidity();
            firstInvalidField.focus();
            return false;
        }
        return true;
    }

    function hideAllSubcategoryBlocks() {
        document.querySelectorAll('.subcategory-block').forEach(el => {
            el.style.display = 'none';
        });
        hideOrderTypeBlocks();
        syncDynamicRequired();
    }

    function hideOrderTypeBlocks() {
        ['block-satisfaccion_adaptacion', 'block-satisfaccion_imagen'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
        syncDynamicRequired();
    }

    function showBlock(id) {
        const el = document.getElementById(id);
        if (el) el.style.display = 'block';
        syncDynamicRequired();
    }

    function updateOrderTypeBlocks() {
        hideOrderTypeBlocks();
        const activeOrderType = Array.from(document.querySelectorAll('.order-type-select'))
            .find(select => isVisible(select) && select.value);
        if (!activeOrderType) return;
        if (activeOrderType.value === 'satisfaccion_adaptacion') {
            showBlock('block-satisfaccion_adaptacion');
        } else if (activeOrderType.value === 'satisfaccion_imagen') {
            showBlock('block-satisfaccion_imagen');
        }
    }

    function updateTonerWarning() {
        const tonerField = form.querySelector('[name="x_toner_below_15"]');
        const warning = document.getElementById('block-toner-warning');
        if (warning && tonerField) {
            warning.style.display = (tonerField.value === 'no') ? 'block' : 'none';
        }
    }

    function handleSubcategoryChange() {
        hideAllSubcategoryBlocks();
        const selectedOption = subcategory.options[subcategory.selectedIndex];
        const code = subcategoryCodes[subcategory.value] || (selectedOption ? (selectedOption.dataset.code || '') : '');
        showBlockForCode(code);
        updateOrderTypeBlocks();
        updateTonerWarning();
    }

    function populateField(name, value) {
        if (value === undefined || value === null || name === 'attachments' || name === 'csrf_token') {
            return;
        }
        const fields = form.querySelectorAll(`[name="${CSS.escape(name)}"]`);
        fields.forEach(field => {
            if (field.type === 'file') {
                return;
            }
            if (field.type === 'radio') {
                field.checked = field.value === value;
                return;
            }
            if (field.type === 'checkbox') {
                field.checked = Boolean(value);
                return;
            }
            field.value = value;
        });
    }

    function restoreSimpleFields() {
        Object.entries(restoredData).forEach(([name, value]) => {
            if (['x_section_id', 'x_category_id', 'x_subcategory_id', 'attachments', 'csrf_token'].includes(name)) {
                return;
            }
            populateField(name, value);
        });
    }

    function loadCategories(section_id, selectedCategoryId = '', selectedSubcategoryId = '') {
        category.innerHTML = '<option value="">-- seleccionar --</option>';
        subcategory.innerHTML = '<option value="">-- seleccionar --</option>';
        category.disabled = true;
        subcategory.disabled = true;

        subcategoryCodes = {};
        currentCategorySlug = '';
        hideAllSubcategoryBlocks();

        if (!section_id) {
            category.disabled = false;
            subcategory.disabled = false;
            return Promise.resolve();
        }

        return fetch('/helpdesk/categories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' },
            body: new URLSearchParams({ section_id: section_id })
        })
        .then(res => {
            if (!res.ok) throw new Error('Error cargando categorías');
            return res.json();
        })
        .then(data => {
            const frag = document.createDocumentFragment();
            data.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = c.name;
                opt.dataset.slug = c.slug || c.code || '';
                frag.appendChild(opt);
            });
            category.appendChild(frag);
            category.disabled = false;
            subcategory.disabled = false;

            if (selectedCategoryId) {
                category.value = String(selectedCategoryId);
                const selectedOpt = category.options[category.selectedIndex];
                currentCategorySlug = selectedOpt ? (selectedOpt.dataset.slug || '') : '';
                return loadSubcategories(selectedCategoryId, selectedSubcategoryId);
            }
            return Promise.resolve();
        })
        .catch(err => {
            console.error(err);
            category.disabled = false;
            subcategory.disabled = false;
        });
    }

    function loadSubcategories(category_id, selectedSubcategoryId = '') {
        const selectedOpt = category.options[category.selectedIndex];
        currentCategorySlug = selectedOpt ? (selectedOpt.dataset.slug || '') : '';

        subcategory.innerHTML = '<option value="">-- seleccionar --</option>';
        subcategory.disabled = true;

        subcategoryCodes = {};
        hideAllSubcategoryBlocks();

        if (!category_id) {
            subcategory.disabled = false;
            return Promise.resolve();
        }

        return fetch('/helpdesk/subcategories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' },
            body: new URLSearchParams({ category_id: category_id })
        })
        .then(res => {
            if (!res.ok) throw new Error('Error cargando subcategorías');
            return res.json();
        })
        .then(data => {
            const frag = document.createDocumentFragment();
            data.forEach(sc => {
                const opt = document.createElement('option');
                opt.value = sc.id;
                opt.textContent = sc.name;
                opt.dataset.code = sc.code || '';
                frag.appendChild(opt);
                subcategoryCodes[sc.id] = sc.code || '';
            });
            subcategory.appendChild(frag);
            subcategory.disabled = false;

            if (selectedSubcategoryId) {
                subcategory.value = String(selectedSubcategoryId);
                handleSubcategoryChange();
            }
        })
        .catch(err => {
            console.error(err);
            subcategory.disabled = false;
        });
    }

    function restoreFormData() {
        if (!Object.keys(restoredData).length) {
            syncDynamicRequired();
            return;
        }

        restoreSimpleFields();

        const sectionId = restoredData.x_section_id || '';
        const categoryId = restoredData.x_category_id || '';
        const subcategoryId = restoredData.x_subcategory_id || '';

        if (sectionId) {
            section.value = String(sectionId);
        }

        loadCategories(sectionId, categoryId, subcategoryId).then(() => {
            restoreSimpleFields();
            updateOrderTypeBlocks();
            updateTonerWarning();
            syncDynamicRequired();
        });
    }

    function showBlockForCode(code) {
        if (!code) return;

        if (REFACTURACION_CODES.includes(code)) {
            showBlock('block-refacturacion');
            return;
        }

        if (CONVENIOS_CODES.includes(code)) {
            showBlock('block-convenios');
            return;
        }

        // NUEVO: receta LC
        if (currentCategorySlug === 'receta_lc_lente_contacto' && code === 'atraso_lente_contacto') {
            showBlock('block-receta_lc_atraso_lente_contacto');
            return;
        }

        // NUEVO: papelería seguimiento
        if (currentCategorySlug === 'papeleria_seguimiento' && code === 'seguimiento_solicitud') {
            showBlock('block-papeleria_seguimiento');
            return;
        }

        if (currentCategorySlug === 'dev_real_tc_db') {
            if (DEV_REAL_TC_DB_CODES.includes(code)) {
                showBlock('block-dev-real-tc-db');
                const extraId = DEV_TC_EXTRA_BLOCKS[code];
                if (extraId) showBlock(extraId);
                return;
            }
        }

        if (currentCategorySlug === 'dev_real_cash_order') {
            if (DEV_REAL_CASH_ORDER_CODES.includes(code)) {
                showBlock('block-dev-real-cash-order');
                const extraId = DEV_CASH_ORDER_EXTRA_BLOCKS[code];
                if (extraId) showBlock(extraId);
                return;
            }
        }

        if (currentCategorySlug === 'dev_real_cash_transfer') {
            if (DEV_REAL_CASH_TRANSFER_CODES.includes(code)) {
                showBlock('block-dev-real-cash-transfer');
                const extraId = DEV_CASH_TRANSFER_EXTRA_BLOCKS[code];
                if (extraId) showBlock(extraId);
                return;
            }
        }

        const blockId = BLOCK_MAP[code];
        if (blockId) showBlock(blockId);
    }

    section.addEventListener('change', function () {
        loadCategories(this.value);
    });

    category.addEventListener('change', function () {
        loadSubcategories(this.value);
    });

    subcategory.addEventListener('change', function () {
        handleSubcategoryChange();
    });

    document.addEventListener('change', function (e) {
        if (!e.target.classList.contains('order-type-select')) return;
        updateOrderTypeBlocks();
    });

    document.addEventListener('change', function (e) {
        if (e.target.name !== 'x_toner_below_15') return;
        updateTonerWarning();
    });

    form.addEventListener('submit', function (e) {
        if (!validateDynamicFields()) {
            e.preventDefault();
        }
    });

    form.addEventListener('change', function (e) {
        if (e.target.matches('.subcategory-block input, .subcategory-block select, .subcategory-block textarea, #block-satisfaccion_adaptacion input, #block-satisfaccion_adaptacion select, #block-satisfaccion_adaptacion textarea, #block-satisfaccion_imagen input, #block-satisfaccion_imagen select, #block-satisfaccion_imagen textarea')) {
            e.target.setCustomValidity('');
            if (e.target.type === 'radio' && e.target.name) {
                form.querySelectorAll(`input[type="radio"][name="${CSS.escape(e.target.name)}"]`).forEach(radio => {
                    radio.setCustomValidity('');
                });
            }
        }
    });

    restoreFormData();

});
