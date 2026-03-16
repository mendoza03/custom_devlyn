window.addEventListener('load', function () {

    const section     = document.getElementById('section');
    const category    = document.getElementById('category');
    const subcategory = document.getElementById('subcategory');

    if (!section || !category || !subcategory) return;

    // -------------------------------------------------------
    // Mapa: subcategory_code -> id del bloque en el DOM
    // -------------------------------------------------------
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
    };

    // Refacturación: varios codes apuntan al mismo bloque
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

    // Cache { subcategory_id: code }
    let subcategoryCodes = {};

    // -------------------------------------------------------
    // Helpers
    // -------------------------------------------------------
    function hideAllSubcategoryBlocks() {
        document.querySelectorAll('.subcategory-block').forEach(el => {
            el.style.display = 'none';
        });
        hideOrderTypeBlocks();
    }

    function hideOrderTypeBlocks() {
        ['block-satisfaccion_adaptacion', 'block-satisfaccion_imagen'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
    }

    function showBlock(id) {
        const el = document.getElementById(id);
        if (el) el.style.display = 'block';
    }

    function showBlockForCode(code) {
        if (!code) return;
        if (REFACTURACION_CODES.includes(code)) {
            showBlock('block-refacturacion');
            return;
        }
        const blockId = BLOCK_MAP[code];
        if (blockId) showBlock(blockId);
    }

    // -------------------------------------------------------
    // Sección → categorías
    // -------------------------------------------------------
    section.addEventListener('change', function () {
        const section_id = this.value;

        category.innerHTML = '<option value="">-- seleccionar --</option>';
        subcategory.innerHTML = '<option value="">-- seleccionar --</option>';
        subcategoryCodes = {};
        hideAllSubcategoryBlocks();

        if (!section_id) return;

        category.disabled = true;

        fetch('/helpdesk/categories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ section_id })
        })
        .then(res => { if (!res.ok) throw new Error('Error'); return res.json(); })
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
        .catch(err => { console.error(err); category.disabled = false; });
    });

    // -------------------------------------------------------
    // Categoría → subcategorías  (el endpoint ahora devuelve "code")
    // -------------------------------------------------------
    category.addEventListener('change', function () {
        const category_id = this.value;

        subcategory.innerHTML = '<option value="">-- seleccionar --</option>';
        subcategoryCodes = {};
        hideAllSubcategoryBlocks();

        if (!category_id) return;

        subcategory.disabled = true;

        fetch('/helpdesk/subcategories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ category_id })
        })
        .then(res => { if (!res.ok) throw new Error('Error'); return res.json(); })
        .then(data => {
            const frag = document.createDocumentFragment();
            data.forEach(sc => {
                const opt = document.createElement('option');
                opt.value = sc.id;
                opt.textContent = sc.name;
                frag.appendChild(opt);
                // Guardamos el code para usarlo al seleccionar
                subcategoryCodes[sc.id] = sc.code || '';
            });
            subcategory.appendChild(frag);
            subcategory.disabled = false;
        })
        .catch(err => { console.error(err); subcategory.disabled = false; });
    });

    // -------------------------------------------------------
    // Subcategoría → mostrar bloque por code
    // -------------------------------------------------------
    subcategory.addEventListener('change', function () {
        hideAllSubcategoryBlocks();
        const code = subcategoryCodes[this.value] || '';
        showBlockForCode(code);
    });

    // -------------------------------------------------------
    // x_order_type → sub-bloques adaptación / imagen
    // Usa delegación para capturar cualquier .order-type-select
    // -------------------------------------------------------
    document.addEventListener('change', function (e) {
        if (!e.target.classList.contains('order-type-select')) return;
        hideOrderTypeBlocks();
        if (e.target.value === 'satisfaccion_adaptacion') {
            showBlock('block-satisfaccion_adaptacion');
        } else if (e.target.value === 'satisfaccion_imagen') {
            showBlock('block-satisfaccion_imagen');
        }
    });

    // -------------------------------------------------------
    // Tóner: advertencia cuando selecciona "no" (>15%)
    // -------------------------------------------------------
    document.addEventListener('change', function (e) {
        if (e.target.id !== 'x_toner_below_15') return;
        const warning = document.getElementById('block-toner-warning');
        if (warning) {
            warning.style.display = (e.target.value === 'no') ? 'block' : 'none';
        }
    });

});