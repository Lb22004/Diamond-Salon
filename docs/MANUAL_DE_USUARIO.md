# MANUAL DE USUARIO — SISTEMA INTEGRADO DIAMOND SALÓN
## Atelier Contable & Control Operativo bajo NIIF para las PYMES
**Versión del Sistema:** 2.0 (Release Noviembre 2026)  
**Entorno de Operación:** Local Docker (`http://localhost:5173` / `http://localhost:8000`)  
**Marco Legal y Técnico:** NIIF para las PYMES · Ley de Impuesto a la Transferencia de Bienes Muebles y a la Prestación de Servicios (Ley de IVA) · Código Tributario de El Salvador.

---

## 1. INTRODUCCIÓN Y ARQUITECTURA DEL SISTEMA

El sistema **Diamond Salón — Atelier Contable** es una plataforma tecnológica integral diseñada específicamente para salones de belleza, estéticas y ateliers que requieren un control riguroso de inventarios, facturación fiscal y contabilidad formal en estricto cumplimiento con la normativa contable internacional (**NIIF para las PYMES**) y las leyes tributarias de la República de El Salvador.

```
+-----------------------------------------------------------------------------------+
|                           DIAMOND SALÓN — ATELIER CONTABLE                         |
+-----------------------------------------------------------------------------------+
|  [VISTA 1] Panel General & Indicadores Financieros (KPIs en tiempo real)          |
|  [VISTA 2] Catálogo de Cuentas NIIF PYMES (82 cuentas decimales oficiales)        |
|  [VISTA 3] Inventario Mixto (Separación estricta Vitrina Reventa vs. Cabina Insumos)|
|  [VISTA 4] Libro de Ventas (Facturas FCF / Crédito Fiscal CCF / Retención 1%)     |
|  [VISTA 5] Libro de Compras (Crédito Fiscal 13% / Clasificación de Destino)       |
|  [VISTA 6] Libro Diario & Mayor Simultáneo en T (Dualidad Debe = Haber)           |
|  [CIERRE]  Cierre Contable Mensual & Liquidación Automática de IVA (Art. 54-57)   |
+-----------------------------------------------------------------------------------+
```

### Principios Fundamentales del Sistema
1. **Regla de Oro RN-07 (Separación Vitrina vs. Cabina):** El inventario de venta comercial al mostrador (`110401 Mercadería vitrina`) no se mezcla bajo ninguna circunstancia con los insumos químicos o técnicos usados en tocador/cabina (`110402 Insumos cabina`).
2. **Dualidad Contable Inmutable (RN-11):** Toda operación económica (venta, compra, consumo, merma o cobro) produce inmediatamente un asiento contable cuadrado donde `Σ Debe = Σ Haber`.
3. **Conciliación Perpetua Kárdex-Mayor (RN-13):** La sumatoria del inventario físico valorado mediante el método de Costo Promedio Ponderado concilia al 100% con los saldos deudores de las cuentas de mayor `110401` y `110402`.
4. **Trazabilidad Fiscal Salvadoreña:** Emisión correlativa de Comprobantes de Crédito Fiscal (CCF) y Facturas de Consumidor Final (FCF), control de retención del 1% para Grandes Contribuyentes y liquidación mensual de IVA Débito vs. IVA Crédito Fiscal.

---

## 2. ROLES DE USUARIO, CREDENCIALES Y MATRIZ RBAC

El acceso a Diamond Salón está protegido mediante autenticación JSON Web Tokens (JWT) y una matriz de control de acceso basado en roles (RBAC) que asegura que cada colaborador ejecute exclusivamente las funciones pertinentes a su cargo.

### 2.1 Credenciales de Acceso Configuradas

| Usuario | Nombre Completo | Cargo Oficial | Rol en Sistema | Contraseña |
| :--- | :--- | :--- | :--- | :--- |
| **`admin`** | Maira Gómez | Administradora General | `ADMIN` | `Admin123!*` |
| **`contador`** | Jose Roberto | Auditor Líder del Atelier | `ACCOUNTANT` | `Contador123!*` |
| **`compras`** | Víctor Flores | Jefe de Compras y Almacén | `PURCHASING` | `Compras123!*` |
| **`estilista`**| Ferdinand Silva | Estilista Profesional / Cajero | `CASHIER` | `Estilista123!*` |

> [!IMPORTANT]
> Las contraseñas están protegidas en el backend mediante el algoritmo criptográfico PBKDF2 con salt individual. En el primer inicio de sesión se recomienda actualizar la contraseña desde el menú de usuario.

### 2.2 Matriz de Privilegios y Acceso por Módulo

| Módulo / Funcionalidad | `ADMIN` | `ACCOUNTANT` (Contador) | `PURCHASING` (Compras) | `CASHIER` (Estilista) |
| :--- | :---: | :---: | :---: | :---: |
| **Panel General (Dashboard)** | Lectura / Escritura | Lectura | Lectura | Solo KPIs propios |
| **Catálogo de Cuentas** | Total | Total (Crea subcuentas) | Solo lectura | Sin acceso |
| **Inventario Mixto** | Total | Total | Entradas / Ajustes | Consumo cabina |
| **Libro de Ventas** | Total | Auditoría / Reporte | Sin acceso | Registro FCF / CCF |
| **Libro de Compras** | Total | Auditoría / Reporte | Registro CCF Proveedor | Sin acceso |
| **Libro Diario y Mayor** | Total | Total | Sin acceso | Sin acceso |
| **Cierre Mensual de Período** | Aprobación | Ejecución / Bloqueo | Sin acceso | Sin acceso |
| **Administración de Usuarios** | Total | Sin acceso | Sin acceso | Sin acceso |

---

## 3. CATÁLOGO OFICIAL DE CUENTAS (TABLA 1 - NIIF PARA LAS PYMES)

El sistema incorpora de manera predeterminada las **82 cuentas contables oficiales** codificadas bajo el estándar decimal de 4 niveles jerárquicos:
* **Nivel 1 (1 dígito):** Clase de Cuenta (`1 ACTIVO`, `2 PASIVO`, `3 PATRIMONIO`, `4 COSTOS Y GASTOS`, `5 INGRESOS`).
* **Nivel 2 (2 dígitos):** Grupo Contable (`11 ACTIVO CORRIENTE`, `21 PASIVO CORRIENTE`, etc.).
* **Nivel 3 (4 dígitos):** Cuenta de Mayor (`1101 Efectivo y equivalentes`, `1104 Inventarios`, etc.).
* **Nivel 4 (6 dígitos):** Subcuenta Analítica Imputable (`110101 Caja general`, `110401 Inventario vitrina`, etc.).

> [!NOTE]
> Solo las cuentas de **Nivel 4 (Subcuentas Analíticas)** aceptan imputación contable directa en asientos de diario. Las cuentas de Nivel 1, 2 y 3 son sintéticas y acumulan saldos automáticamente.

### Listado Completo de las 82 Cuentas del Catálogo

| Código | Denominación de la Cuenta | Nivel | Naturaleza | Clasificación / Propósito | Reglas de Cargo y Abono |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **`1`** | **ACTIVO** | 1 | Deudora | Clase principal | Se carga por aumentos de recursos; se abona por disminuciones. |
| **`11`** | **ACTIVO CORRIENTE** | 2 | Deudora | Grupo activo corriente | Recursos realizables o convertibles en efectivo en ≤ 12 meses. |
| **`1101`** | Efectivo y equivalentes al efectivo | 3 | Deudora | Mayor de disponibilidades | Efectivo en mano y depósitos en instituciones bancarias. |
| `110101` | Caja general | 4 | Deudora | Subcuenta analítica | **Cargo:** Cobros en efectivo de ventas/servicios. **Abono:** Remesas y pagos. |
| `110102` | Caja chica | 4 | Deudora | Subcuenta analítica | **Cargo:** Apertura o reposición de fondo fijo. **Abono:** Liquidación del fondo. |
| `110103` | Bancos cuenta corriente | 4 | Deudora | Subcuenta analítica | **Cargo:** Depósitos, transferencias recibidas, cobros POS. **Abono:** Transferencias/cheques. |
| `110104` | Bancos cuenta de ahorro | 4 | Deudora | Subcuenta analítica | **Cargo:** Depósitos e intereses devengados. **Abono:** Retiros o traslados. |
| **`1102`** | Cuentas y documentos por cobrar | 3 | Deudora | Mayor exigible | Créditos otorgados documentados comercialmente. |
| `110201` | Clientes | 4 | Deudora | Subcuenta analítica | **Cargo:** Facturas al crédito a clientes corporativos. **Abono:** Cancelación o abonos. |
| `110202` | Deudores diversos | 4 | Deudora | Subcuenta analítica | **Cargo:** Préstamos o anticipos a colaboradores. **Abono:** Cobros recibidos. |
| `110203` | Estimación para cuentas incobrables (-) | 4 | Acreedora | Cuenta de valuación | **Cargo:** Castigo de cuentas prescritas. **Abono:** Provisión por deterioro. |
| **`1103`** | IVA crédito fiscal | 3 | Deudora | Mayor tributario | Impuesto al valor agregado pagado a favor del contribuyente. |
| `110301` | IVA crédito fiscal por compras | 4 | Deudora | Subcuenta analítica | **Cargo:** 13% IVA soportado en CCF de proveedores. **Abono:** Liquidación mensual contra débito. |
| **`1104`** | Inventarios | 3 | Deudora | Mayor de existencias | Existencias de mercaderías e insumos valuados a costo promedio. |
| `110401` | Inventario de mercadería para la venta (vitrina) | 4 | Deudora | Subcuenta retail | **Cargo:** Compras CCF de productos de reventa. **Abono:** Costo de venta retail. |
| `110402` | Inventario de insumos para servicios (cabina) | 4 | Deudora | Subcuenta operativa | **Cargo:** Compras CCF de químicos/tintes. **Abono:** Consumo técnico en servicios. |
| **`1105`** | Pagos anticipados | 3 | Deudora | Mayor transitorio | Erogaciones efectuadas por bienes o servicios a devengar. |
| `110501` | Anticipo a proveedores | 4 | Deudora | Subcuenta analítica | **Cargo:** Pagos anticipados a distribuidoras. **Abono:** Recepción de factura/mercadería. |
| `110502` | Seguros pagados por anticipado | 4 | Deudora | Subcuenta analítica | **Cargo:** Póliza anual contra daños/robo. **Abono:** Amortización mensual a gasto. |
| **`12`** | **ACTIVO NO CORRIENTE** | 2 | Deudora | Grupo bienes duraderos | Activos tangibles e intangibles destinados al uso operativo. |
| **`1201`** | Propiedad, planta y equipo | 3 | Deudora | Mayor activo fijo | Bienes tangibles con vida útil superior a un año. |
| `120101` | Mobiliario y equipo de salón | 4 | Deudora | Subcuenta analítica | **Cargo:** Sillones hidráulicos, lavacabezas, secadores de pie. **Abono:** Baja o venta. |
| `120102` | Equipo de cómputo | 4 | Deudora | Subcuenta analítica | **Cargo:** Terminales POS, computadoras de caja, tablets. **Abono:** Descarte tecnológico. |
| `120103` | Mobiliario y equipo de oficina | 4 | Deudora | Subcuenta analítica | **Cargo:** Escritorios, salas de espera, vitrinas exhibidoras. **Abono:** Retiro. |
| `120104` | Depreciación acumulada (-) | 4 | Acreedora | Cuenta de valuación | **Cargo:** Liquidación por venta del bien. **Abono:** Depreciación sistemática mensual. |
| **`1202`** | Activos intangibles | 3 | Deudora | Mayor intangibles | Software y licencias operativas de uso continuo. |
| `120201` | Programas informáticos (software) | 4 | Deudora | Subcuenta analítica | **Cargo:** Adquisición de licencias y software de gestión. **Abono:** Amortización acumulada. |
| `120202` | Amortización acumulada de software (-) | 4 | Acreedora | Cuenta de valuación | **Cargo:** Baja de licencia. **Abono:** Cuota mensual de amortización. |
| **`2`** | **PASIVO** | 1 | Acreedora | Clase principal | Obligaciones presentes del atelier derivadas de hechos pasados. |
| **`21`** | **PASIVO CORRIENTE** | 2 | Acreedora | Grupo deudas corto plazo| Obligaciones exigibles dentro del ciclo de 12 meses. |
| **`2101`** | Cuentas y documentos por pagar comerciales | 3 | Acreedora | Mayor proveedores | Deudas comerciales con distribuidores por compras a crédito. |
| `210101` | Proveedores nacionales | 4 | Acreedora | Subcuenta analítica | **Cargo:** Pagos efectuados a proveedores. **Abono:** CCF recibidos a crédito. |
| `210102` | Proveedores extranjeros | 4 | Acreedora | Subcuenta analítica | **Cargo:** Liquidación de importaciones. **Abono:** Facturas de importación pendientes. |
| **`2102`** | IVA débito fiscal | 3 | Acreedora | Mayor tributario | Impuesto al valor agregado retenido en ventas a clientes. |
| `210201` | IVA débito fiscal por ventas | 4 | Acreedora | Subcuenta analítica | **Cargo:** Liquidación mensual contra crédito fiscal. **Abono:** 13% IVA en FCF y CCF emitidos. |
| **`2103`** | Impuestos y contribuciones por pagar | 3 | Acreedora | Mayor fisco | Gravámenes y retenciones pendientes de enterar al Ministerio de Hacienda. |
| `210301` | IVA por pagar | 4 | Acreedora | Subcuenta analítica | **Cargo:** Pago en formulario F-07 en banco. **Abono:** Saldo neto resultante del cierre mensual. |
| `210302` | Pago a cuenta de ISR por pagar | 4 | Acreedora | Subcuenta analítica | **Cargo:** Entero mensual del 1.75%. **Abono:** Provisión sobre ingresos brutos mensuales. |
| `210303` | Impuesto sobre la renta por pagar | 4 | Acreedora | Subcuenta analítica | **Cargo:** Pago anual de renta. **Abono:** Provisión del ejercicio fiscal anual. |
| `210304` | Retención de IVA por enterar (1%) | 4 | Acreedora | Subcuenta analítica | **Cargo:** Pago a Hacienda. **Abono:** 1% retenido en compras a terceros. |
| **`2104`** | Beneficios y remuneraciones por pagar | 3 | Acreedora | Mayor laboral | Deudas salariales y prestaciones laborales del personal. |
| `210401` | Sueldos por pagar | 4 | Acreedora | Subcuenta analítica | **Cargo:** Pago de nómina quincenal/mensual. **Abono:** Planilla devengada de estilistas. |
| `210402` | Comisiones a estilistas por pagar | 4 | Acreedora | Subcuenta analítica | **Cargo:** Pago de comisiones quincenales. **Abono:** % comisiones sobre servicios realizados. |
| `210403` | Retención ISSS laboral | 4 | Acreedora | Subcuenta analítica | **Cargo:** Pago a Tesorería ISSS. **Abono:** 3% deducido al trabajador. |
| `210404` | Retención AFP laboral | 4 | Acreedora | Subcuenta analítica | **Cargo:** Pago a AFP Crecer / Confía. **Abono:** 7.25% deducido al trabajador. |
| `210405` | Cuota patronal ISSS por pagar | 4 | Acreedora | Subcuenta analítica | **Cargo:** Pago integral mensual ISSS. **Abono:** 7.5% aporte patronal salón. |
| `210406` | Cuota patronal AFP por pagar | 4 | Acreedora | Subcuenta analítica | **Cargo:** Pago mensual AFP. **Abono:** 8.75% aporte patronal salón. |
| `210407` | Aguinaldos por pagar | 4 | Acreedora | Subcuenta analítica | **Cargo:** Pago en diciembre. **Abono:** Provisión mensual de aguinaldo. |
| `210408` | Vacaciones por pagar | 4 | Acreedora | Subcuenta analítica | **Cargo:** Pago al disfrutar vacación. **Abono:** Provisión del 30% recargo vacacional. |
| **`2105`** | Préstamos y sobregiros bancarios | 3 | Acreedora | Mayor pasivo bancario | Créditos bancarios y líneas de sobregiro vigentes. |
| `210501` | Préstamos bancarios a corto plazo | 4 | Acreedora | Subcuenta analítica | **Cargo:** Pago de cuotas de capital. **Abono:** Desembolsos bancarios recibidos. |
| **`22`** | **PASIVO NO CORRIENTE** | 2 | Acreedora | Grupo largo plazo | Obligaciones con vencimiento superior a un ejercicio contable. |
| **`2201`** | Obligaciones a largo plazo | 3 | Acreedora | Mayor largo plazo | Financiamiento estructurado de largo plazo. |
| `220101` | Préstamos bancarios a largo plazo | 4 | Acreedora | Subcuenta analítica | **Cargo:** Traslado a corto plazo. **Abono:** Préstamos de inversión inicial. |
| **`3`** | **PATRIMONIO** | 1 | Acreedora | Clase patrimonio | Participación residual en los activos del salón tras deducir pasivos. |
| **`31`** | **CAPITAL CONTABLE** | 2 | Acreedora | Grupo aportaciones | Capital suscrito y pagado por los socios fundadores. |
| **`3101`** | Capital social | 3 | Acreedora | Mayor capital | Capital registrado ante el Registro de Comercio. |
| `310101` | Capital social pagado | 4 | Acreedora | Subcuenta analítica | **Cargo:** Reducciones de capital. **Abono:** Aportes constitutivos del Atelier. |
| **`32`** | **RESERVAS Y RESULTADOS ACUMULADOS**| 2 | Acreedora | Grupo reservas y utilidades | Beneficios retenidos y fondos de ley. |
| **`3201`** | Reservas | 3 | Acreedora | Mayor reservas | Reserva legal societaria (7% de la utilidad). |
| `320101` | Reserva legal | 4 | Acreedora | Subcuenta analítica | **Cargo:** Capitalización o absorción de pérdidas. **Abono:** 7% sobre utilidades anuales. |
| **`3202`** | Resultados acumulados | 3 | Acreedora | Mayor resultados | Utilidades y pérdidas de ejercicios contables anteriores. |
| `320201` | Utilidades retenidas | 4 | Acreedora | Subcuenta analítica | **Cargo:** Distribución de dividendos. **Abono:** Cierre anual de ejercicios con beneficio. |
| `320202` | Pérdidas acumuladas (-) | 4 | Deudora | Valuación patrimonial| **Cargo:** Absorción de ejercicios con pérdida. **Abono:** Compensación con utilidades futuras. |
| **`3203`** | Resultados del ejercicio | 3 | Acreedora | Mayor ejercicio actual | Utilidad o pérdida neta del ejercicio en curso. |
| `320301` | Utilidad del ejercicio | 4 | Acreedora | Subcuenta analítica | **Cargo:** Traslado a utilidades retenidas. **Abono:** Cierre anual de ingresos vs gastos. |
| `320302` | Pérdida del ejercicio (-) | 4 | Deudora | Valuación patrimonial| **Cargo:** Saldo deudor al cierre si gastos > ingresos. **Abono:** Traslado patrimonial. |
| **`4`** | **COSTOS Y GASTOS** | 1 | Deudora | Clase egresos | Decrementos en los beneficios económicos producidos en el ejercicio. |
| **`41`** | **COSTO DE VENTAS Y SERVICIOS** | 2 | Deudora | Grupo costos directos | Costos directos de la mercadería vendida y servicios prestados. |
| **`4101`** | Costo de mercadería vendida (vitrina) | 3 | Deudora | Mayor costo vitrina | Costo promedio ponderado de los productos comerciales vendidos. |
| `410101` | Costo de productos para reventa | 4 | Deudora | Subcuenta analítica | **Cargo:** Costo de venta reconocido al emitir FCF/CCF. **Abono:** Cierre anual contra pérdidas y ganancias. |
| **`4102`** | Costo de insumos de servicios (cabina) | 3 | Deudora | Mayor costo cabina | Insumos técnicos utilizados por los estilistas en tratamientos. |
| `410201` | Insumos consumidos en servicios | 4 | Deudora | Subcuenta analítica | **Cargo:** Consumo técnico registrado en cabina. **Abono:** Cierre anual a liquidación de resultados. |
| **`42`** | **GASTOS DE OPERACIÓN** | 2 | Deudora | Grupo gastos operativos | Erogaciones necesarias para la gestión comercial y administrativa. |
| **`4201`** | Gastos de administración | 3 | Deudora | Mayor administración | Sueldos, alquileres, servicios básicos y mermas del salón. |
| `420101` | Sueldos y salarios administrativos | 4 | Deudora | Subcuenta analítica | **Cargo:** Salarios de gerencia y recepción. **Abono:** Cierre contable anual. |
| `420102` | Mermas y deterioro de inventario | 4 | Deudora | Subcuenta analítica | **Cargo:** Ajustes por envases rotos, vencidos o diferencias en conteo. **Abono:** Cierre anual. |
| `420103` | Alquiler de local comercial | 4 | Deudora | Subcuenta analítica | **Cargo:** Canon mensual de arrendamiento del salón. **Abono:** Cierre anual. |
| `420104` | Energía eléctrica | 4 | Deudora | Subcuenta analítica | **Cargo:** Facturas de CAESS / Delsur. **Abono:** Cierre anual. |
| `420105` | Agua potable | 4 | Deudora | Subcuenta analítica | **Cargo:** Factura mensual de ANDA. **Abono:** Cierre anual. |
| `420106` | Telecomunicaciones e internet | 4 | Deudora | Subcuenta analítica | **Cargo:** Servicio de fibra óptica y telefonía. **Abono:** Cierre anual. |
| `420107` | Depreciación mobiliario y equipo | 4 | Deudora | Subcuenta analítica | **Cargo:** Gasto mensual por depreciación lineal de mobiliario. **Abono:** Cierre anual. |
| `420108` | Amortización de software | 4 | Deudora | Subcuenta analítica | **Cargo:** Cuota mensual de amortización de licencias. **Abono:** Cierre anual. |
| `420109` | Honorarios profesionales | 4 | Deudora | Subcuenta analítica | **Cargo:** Auditoría externa y servicios contables. **Abono:** Cierre anual. |
| `420110` | Papelería y útiles de oficina | 4 | Deudora | Subcuenta analítica | **Cargo:** Insumos administrativos y de recepción. **Abono:** Cierre anual. |
| **`4202`** | Gastos de venta | 3 | Deudora | Mayor comerciales | Erogaciones destinadas a promocionar y vender en el atelier. |
| `420201` | Comisiones sobre servicios y ventas | 4 | Deudora | Subcuenta analítica | **Cargo:** Comisiones devengadas por estilistas. **Abono:** Cierre anual. |
| `420202` | Publicidad y mercadeo | 4 | Deudora | Subcuenta analítica | **Cargo:** Campañas en redes sociales, pauta y material POP. **Abono:** Cierre anual. |
| `420203` | Comisiones bancarias POS | 4 | Deudora | Subcuenta analítica | **Cargo:** % de retención por transacciones con tarjeta POS. **Abono:** Cierre anual. |
| **`43`** | **GASTOS FINANCIEROS Y OTROS** | 2 | Deudora | Grupo otros gastos | Intereses bancarios e imprevistos. |
| **`4301`** | Gastos financieros | 3 | Deudora | Mayor financiero | Costos por financiamiento bancario. |
| `430101` | Intereses bancarios | 4 | Deudora | Subcuenta analítica | **Cargo:** Intereses cobrados en préstamos. **Abono:** Cierre anual. |
| **`4302`** | Otros gastos | 3 | Deudora | Mayor no operacionales | Pérdidas extraordinarias no vinculadas a la actividad principal. |
| `430201` | Gastos extraordinarios | 4 | Deudora | Subcuenta analítica | **Cargo:** Siniestros o penalizaciones. **Abono:** Cierre anual. |
| **`5`** | **INGRESOS** | 1 | Acreedora | Clase ingresos | Incrementos en beneficios económicos por actividades ordinarias. |
| **`51`** | **INGRESOS DE ACTIVIDADES ORDINARIAS**| 2 | Acreedora | Grupo ingresos corrientes| Facturación por prestación de servicios y reventa de cosméticos. |
| **`5101`** | Ingresos por servicios de belleza | 3 | Acreedora | Mayor servicios salón | Ingresos netos devengados por atenciones en salón (Cabina). |
| `510101` | Peluquería (corte, tinte, peinado) | 4 | Acreedora | Subcuenta analítica | **Cargo:** Cancelaciones al cierre anual. **Abono:** Base imponible gravada de servicios capilares. |
| `510102` | Manos y pies (manicura, pedicura) | 4 | Acreedora | Subcuenta analítica | **Cargo:** Cierre anual. **Abono:** Base gravada de manicura/pedicura. |
| `510103` | Maquillaje y tratamientos faciales | 4 | Acreedora | Subcuenta analítica | **Cargo:** Cierre anual. **Abono:** Base gravada de estética facial. |
| **`5102`** | Ingresos por venta de productos | 3 | Acreedora | Mayor retail mostrador | Venta directa de productos cosméticos al cliente final. |
| `510201` | Venta de cosméticos y productos capilares | 4 | Acreedora | Subcuenta analítica | **Cargo:** Cierre anual. **Abono:** Base gravada de venta en mostrador (Vitrina). |
| **`5103`** | Otros ingresos | 3 | Acreedora | Mayor ingresos varios | Rentas accesorias y sobrantes justificados. |
| `510301` | Ingresos varios | 4 | Acreedora | Subcuenta analítica | **Cargo:** Cierre anual. **Abono:** Ajustes positivos de inventario o ingresos no ordinarios. |

---

## 4. MANUAL OPERATIVO POR MÓDULOS

---

### MÓDULO 1: PANEL GENERAL (DASHBOARD)
**Ruta:** `/dashboard`  
**Objetivo:** Proporcionar al administrador y contador una panorámica visual ejecutiva del estado económico, fiscal y operativo del salón en el período contable seleccionado.

#### Elementos Clave del Panel:
1. **Selector de Período Fiscal:** Permite alternar entre períodos contables mensuales (ej. `Noviembre 2026`). Si el período está cerrado, el sistema muestra una insignia visual ámbar de solo lectura.
2. **Tarjetas de Rendimiento (KPIs):**
   * **Ventas Brutas Acumuladas:** Suma total facturada en FCF y CCF del mes corriente.
   * **Base Imponible Neta:** Ingresos reales del salón antes de IVA (divididos entre Servicios `510101` y Vitrina `510201`).
   * **IVA Débito Fiscal Acumulado:** Monto del 13% de IVA retenido a enterar en liquidación.
   * **Disponibilidad en Caja y Bancos:** Saldo conciliado en cuentas `110101` y `110103`.
3. **Semáforos de Salud Contable:**
   * **Integridad Dual:** Indicador verde si `Σ Debe == Σ Haber` (diferencia `$0.00`).
   * **Auditoría de Documentos:** Verifica que el 100% de las ventas y compras tengan su partida contable asociada.
   * **Alerta de Stock Crítico:** Identifica insumos o mercaderías cuya existencia física esté en o por debajo del umbral mínimo configurado.

---

### MÓDULO 2: CATÁLOGO DE CUENTAS
**Ruta:** `/accounting/accounts`  
**Objetivo:** Consultar la estructura jerárquica de 82 cuentas NIIF para PYMES y administrar nuevas subcuentas analíticas.

#### Procedimiento para Crear una Subcuenta Analítica:
1. Inicie sesión con el rol `ADMIN` o `ACCOUNTANT`.
2. Diríjase a la vista **Catálogo de Cuentas**.
3. Localice la cuenta de mayor padre (Nivel 3). Por ejemplo: `4201 Gastos de administración`.
4. Haga clic en el botón superior **"+ Nueva Subcuenta"**.
5. Complete el formulario con los siguientes datos:
   * **Código:** Ingrese un código decimal de 6 dígitos que inicie con los 4 dígitos de la cuenta padre (ej. `420111`).
   * **Nombre:** Denominación clara de la subcuenta (ej. `Seguridad y vigilancia privada`).
   * **Cuenta Padre:** Seleccione la cuenta padre correspondiente (`4201`).
   * **Naturaleza:** Se hereda automáticamente de la clase de cuenta (Deudora para activo/costo/gasto; Acreedora para pasivo/patrimonio/ingreso).
   * **Acepta Movimientos:** Marque la casilla como `Sí` (True).
6. Presione **"Guardar Subcuenta"**. El sistema validará la jerarquía y registrará la auditoría en la base de datos.

---

### MÓDULO 3: INVENTARIO MIXTO (VITRINA VS. CABINA)
**Ruta:** `/inventory`  
**Objetivo:** Garantizar la estricta separación física y contable entre los productos comercializados en vitrina y los insumos técnicos consumidos en las estaciones de servicio.

#### Estructura Visual de la Vista:
* **Columna Izquierda (Rojo Vino / Burdeos — Vitrina Reventa):**
  * Controla productos destinados exclusivamente a la venta retail directa (champús para llevar, mascarillas, sérums).
  * Imputación contable de entrada: `110401 Inventario vitrina`.
  * Requiere obligatoriamente un **Precio de Venta al Público (PVP)** con IVA incluido.
* **Columna Derecha (Negro Grafito / Dorado — Cabina Insumos):**
  * Controla los químicos técnicos, tintes, peróxidos y solventes de uso profesional.
  * Imputación contable de entrada: `110402 Inventario cabina`.
  * **Regla Inquebrantable:** El sistema bloquea a nivel de base de datos (`ck_inventory_cabina_no_pvp`) cualquier intento de fijar precio de venta (`PVP = NULL`), ya que los insumos no se comercializan de manera individual.

#### Flujo Operativo 1: Registro de Ajuste de Inventario (Mermas / Sobrantes)
1. En la parte superior de la vista, haga clic en el botón **"Ajuste de stock"**.
2. Seleccione el tipo de ajuste:
   * **Faltante / Merma:** Envases quebrados, vencimientos o diferencias en conteo físico.
   * **Sobrante:** Conteo físico superior al registrado en Kárdex.
3. Seleccione el producto y la ubicación (`Vitrina`, `Cabina 1`, `Cabina 2` o `Almacén General`).
4. Indique la cantidad física a ajustar y justifique el motivo.
5. Al hacer clic en **"Confirmar Ajuste"**:
   * El sistema genera un movimiento inmutable en `inventory_movement`.
   * Si es merma de Vitrina: Se carga la cuenta `420102 Mermas y deterioro` y se abona `110401 Inventario vitrina`.
   * Si es sobrante: Se carga `110401` y se abona `510301 Ingresos varios`.

#### Flujo Operativo 2: Consumo Técnico en Estaciones (Cabina)
1. El estilista o administrador selecciona el producto técnico (ej. `CAB-001 Tinte Majirel Tubos 50ml`).
2. Registra el consumo asignando el estilista responsable y la estación de trabajo (`Cabina 1` o `Cabina 2`).
3. El motor contable genera de forma automática la partida:
   * **Debe:** `410201 Insumos consumidos en servicios` (Costo directo).
   * **Haber:** `110402 Inventario de insumos para servicios (cabina)`.

---

### MÓDULO 4: LIBRO DE VENTAS E IVA DÉBITO FISCAL
**Ruta:** `/sales/book`  
**Objetivo:** Facturación cronológica de servicios de belleza y productos comerciales, emisión fiscal correlativa y liquidación automática de IVA Débito Fiscal del 13%.

#### Tipos de Comprobantes Admitidos:
* **Factura de Consumidor Final (FCF):** Emitida a clientes particulares (personas naturales sin NRC). El precio mostrado en mostrador ya incluye el 13% de IVA. El sistema desglosa automáticamente la base gravada:
  $$\text{Base Gravada} = \frac{\text{Total Factura}}{1.13}$$
  $$\text{IVA Débito Fiscal (13\%)} = \text{Total Factura} - \text{Base Gravada}$$
* **Comprobante de Crédito Fiscal (CCF):** Emitido a clientes contribuyentes (empresas con NIT y NRC válidos). La base gravada y el IVA se presentan discriminados. Si el cliente es Gran Contribuyente, se deduce automáticamente el 1% de Retención de IVA (Art. 162 del Código Tributario).

#### Procedimiento para Registrar una Venta:
1. Haga clic en el botón **"+ Registrar venta"**.
2. Seleccione la fecha de emisión y el tipo de documento (`FCF` o `CCF`). El sistema asignará el siguiente correlativo autorizado (ej. `FCF-0016`).
3. Seleccione el cliente:
   * Para consumidor común: Seleccione `Consumidor final` o busque al cliente por su nombre o DUI.
   * Para empresas: Seleccione el cliente corporativo; el sistema validará automáticamente su NIT y NRC.
4. Agregue las líneas de la venta:
   * **Servicio (Cabina):** Seleccione el tratamiento capilar, peinado o manicura. La base gravada se dirigirá a `510101`, `510102` o `510103`.
   * **Producto Retail (Vitrina):** Seleccione el producto exhibido. La base gravada se dirigirá a `510201`.
5. Seleccione la forma de pago:
   * `Efectivo (Caja)`: Imputa al Debe de `110101 Caja general`.
   * `Tarjeta POS (Banco)`: Imputa al Debe de `110103 Bancos cuenta corriente`.
   * `Transferencia Bancaria`: Imputa al Debe de `110103 Bancos cuenta corriente`.
   * `Crédito Cliente`: Imputa al Debe de `110201 Clientes`.
6. Al presionar **"Emitir Documento"**, el sistema realiza atómicamente:
   * Emisión del comprobante fiscal.
   * Asiento de Diario automático con partida doble cuadrada.
   * Si incluye producto de Vitrina: Descargo automático de existencias físicas en Kárdex y asiento simultáneo de costo de venta (`Debe 410101` / `Haber 110401`).

---

### MÓDULO 5: LIBRO DE COMPRAS E IVA CRÉDITO FISCAL
**Ruta:** `/purchases/book`  
**Objetivo:** Registro formal de Comprobantes de Crédito Fiscal (CCF) emitidos por proveedores autorizados y control del IVA Crédito Fiscal deducible (Art. 65 Ley de IVA).

#### Procedimiento para Registrar una Compra:
1. Inicie sesión como `admin` o `compras`.
2. Ingrese a la vista **Libro de compras** y presione **"+ Registrar compra"**.
3. Seleccione el proveedor formal (ej. `Distribuidora Bella`, `Insumos Pro`, `Color & Style`). El sistema autocompletará su NIT, NRC y categoría tributaria.
4. Ingrese el número de documento CCF físico (ej. `CCF-4535`) y la fecha de emisión.
5. **Indique el Destino de la Compra (Crucial):**
   * **`VITRINA`:** Para productos que se revenderán al cliente. Carga a `110401 Inventario vitrina`.
   * **`CABINA`:** Para insumos y químicos técnicos de tocador. Carga a `110402 Inventario cabina`.
   * **`GASTO OPERATIVO`:** Para útiles de oficina o servicios generales. Carga a cuentas del grupo `4201`.
6. Añada el detalle de artículos con cantidad y costo neto unitario (sin IVA).
7. Especifique la condición de pago:
   * Si es **Contado**: Seleccione la cuenta de desembolso (`110101 Caja` o `110103 Bancos`).
   * Si es **Crédito**: Indique la fecha de vencimiento (`due_date`) a 30 o 60 días. El sistema registrará la obligación en `210101 Proveedores nacionales`.
8. Haga clic en **"Guardar y Contabilizar"**. Se registrará la entrada física en Kárdex, se recalculará el Costo Promedio Ponderado del producto y se posteará la partida en el Libro Diario.

---

### MÓDULO 6: LIBRO DIARIO Y LIBRO MAYOR
**Ruta:** `/accounting/journal` y `/reports/ledger`  
**Objetivo:** Control cronológico de pólizas contables y visualización analítica en esquema de "Cuentas T" con saldos deudores y acreedores.

#### Libro Diario (`/accounting/journal`):
* Muestra el correlativo estricto de partidas (`Partida #1`, `#2`, etc.).
* Desglosa fecha, concepto descriptivo, cuentas afectadas, cargos y abonos.
* Permite filtrar por tipo de partida: `OPENING` (Apertura), `SALE` (Ventas), `PURCHASE` (Compras), `CONSUMPTION` (Consumos), `ADJUSTMENT` (Ajustes), `CLOSING` (Cierre mensual).
* Las partidas con estado `POSTED` son inmutables. Si se requiere anular una transacción, el sistema emite una **Partida de Reversión Espejo** preservando la pista de auditoría.

#### Libro Mayor Simultáneo en "T" (`/reports/ledger`):
* Muestra de forma interactiva las cuentas principales del atelier contable:
  * `110101 Caja general`
  * `110103 Bancos cuenta corriente`
  * `110401 Inventario mercadería vitrina`
  * `110402 Inventario insumos cabina`
  * `110301 IVA crédito fiscal por compras`
  * `210201 IVA débito fiscal por ventas`
  * `210101 Proveedores nacionales`
  * `510101 Ingresos por servicios de peluquería`
  * `510201 Ingresos por venta de cosméticos`
* Cada tarjeta muestra la columna del **Debe**, la columna del **Haber** y el **Saldo Neto Deudor o Acreedor** resultante al centavo.

---

## 5. GUÍA DEL PROCESO DE CIERRE MENSUAL (WORKFLOW)

El cierre contable mensual es el procedimiento más crítico del ciclo financiero. En Diamond Salón, este flujo está completamente automatizado y protegido contra inconsistencias contables o tributarias.

```
                             FLUJO DE CIERRE CONTABLE MENSUAL
                             
  +---------------------------------------------------------------------------------+
  | 1. VERIFICACIÓN PRE-CIERRE (Pre-close Checklist de 4 filtros obligatorios)       |
  |    [OK] Sin partidas en borrador pendientes (0 drafts)                          |
  |    [OK] Balance de comprobación cuadrado (Σ Debe = Σ Haber)                     |
  |    [OK] 100% de ventas y compras con asiento contable asociado                  |
  |    [OK] Conciliación física Kárdex vs. Mayor (110401 y 110402 sin desfasaje)    |
  +---------------------------------------------------------------------------------+
                                         |
                                         v
  +---------------------------------------------------------------------------------+
  | 2. LIQUIDACIÓN AUTOMÁTICA DE IVA (Art. 54 y 57 Ley de IVA)                      |
  |    IVA Débito Fiscal (210201) vs. IVA Crédito Fiscal (110301)                   |
  |    - Si Débito > Crédito: Se genera obligación a pagar en 210301 IVA por pagar. |
  |    - Si Crédito > Débito: Se genera saldo remanente a favor para el mes siguiente.|
  +---------------------------------------------------------------------------------+
                                         |
                                         v
  +---------------------------------------------------------------------------------+
  | 3. PARTIDA DE CIERRE Y BLOQUEO DEL PERÍODO                                      |
  |    - Se emite automáticamente la partida contable de liquidación.               |
  |    - Se congela el período contable (STATUS = 'CLOSED').                        |
  |    - Se bloquea la creación, modificación o eliminación de datos en dicho mes.  |
  +---------------------------------------------------------------------------------+
```

### Paso a Paso para Ejecutar el Cierre Mensual:
1. Inicie sesión con el rol de **`ACCOUNTANT`** (Jose Roberto).
2. En la barra superior, seleccione el período contable que desea cerrar (ej. `Noviembre 2026`).
3. En la barra lateral izquierda, haga clic en el acceso directo inferior **"Cierre Periódico"** o presione el botón de cierre en el Panel.
4. Se abrirá la ventana modal de **Pre-Close Checklist**:
   * El sistema evaluará en tiempo real los 4 criterios de integridad. Si todos los ítems están en verde (`[OK]`), el botón **"Proceder con el Cierre"** se habilitará.
5. Revise la **Previsualización de la Liquidación de IVA**:
   * Débito Fiscal Acumulado (ej. `$8.06`).
   * Crédito Fiscal Acumulado (ej. `$39.00`).
   * Remanente a Favor del Contribuyente: `$30.94`.
   * Detalle de la partida propuesta:
     * **Cargo (Debe):** `210201 IVA débito fiscal por ventas` por `$8.06` (deja la cuenta en saldo `$0.00`).
     * **Abono (Haber):** `110301 IVA crédito fiscal por compras` por `$8.06` (deja la cuenta con remanente de `$30.94`).
6. Ingrese una nota de cierre facultativa y presione **"Confirmar y Cerrar Período"**.
7. El período pasará de estado `OPEN` a **`CLOSED`**. Se registrará la fecha y el usuario que ejecutó el cierre en `AuditLog`. A partir de este momento, dicho período es legalmente inmutable.

---

## 6. DATOS DE DEMOSTRACIÓN CARGADOS (ESCENARIO NOVIEMBRE 2026)

Para facilitar la evaluación, auditoría y capacitación del personal, el sistema cuenta con un set de datos de prueba precargados correspondientes al ejercicio de **Noviembre 2026**.

### 6.1 Resumen de las 10 Partidas Contables Cuadradas

| Partida | Fecha | Tipo | Descripción de la Operación | Monto Debe | Monto Haber |
| :---: | :---: | :---: | :--- | :---: | :---: |
| **#1** | 01/11/2026 | `OPENING` | Asiento de apertura: Saldos en Caja (`$1,850.00`), Bancos (`$3,400.00`), Vitrina (`$756.00`), Cabina (`$480.00`), Mobiliario (`$4,514.00`) contra Capital Social (`$11,000.00`). | $11,000.00 | $11,000.00 |
| **#2** | 01/11/2026 | `PURCHASE` | Compra CCF-4521 a Distribuidora Bella: Mercadería vitrina al crédito (`$150.00` + IVA `$19.50`). | $169.50 | $169.50 |
| **#3** | 01/11/2026 | `PURCHASE` | Compra CCF-4522 a Insumos Pro: Tintes y peróxidos para cabina al crédito (`$90.00` + IVA `$11.70`). | $101.70 | $101.70 |
| **#4** | 03/11/2026 | `PURCHASE` | Compra CCF-4530 a Color & Style: Tintes orgánicos para cabina al crédito (`$60.00` + IVA `$7.80`). | $67.80 | $67.80 |
| **#5** | 02/11/2026 | `SALE` | Venta FCF-0012 a Ana Mejía: Servicio de corte y peinado en efectivo (`Total $25.00` = Base `$22.12` + IVA `$2.88`). | $25.00 | $25.00 |
| **#6** | 03/11/2026 | `SALE` | Venta FCF-0013 a Consumidor final: Champú nutritivo retail en efectivo (`Total $12.00` = Base `$10.62` + IVA `$1.38`). Simultanéo costo de venta: `$7.00`. | $19.00 | $19.00 |
| **#7** | 04/11/2026 | `SALE` | Venta FCF-0014 a Rosa Flores: Servicio de manicura + esmaltado en efectivo (`Total $15.00` = Base `$13.27` + IVA `$1.73`). | $15.00 | $15.00 |
| **#8** | 05/11/2026 | `SALE` | Venta FCF-0015 a Consumidor final: Sérum de brillo 100ml en efectivo (`Total $18.00` = Base `$15.93` + IVA `$2.07`). Simultáneo costo de venta: `$9.50`. | $27.50 | $27.50 |
| **#9** | 07/11/2026 | `CONSUMPTION` | Consumo técnico en estaciones: Tintes y solventes usados en salón (`$80.00`). | $80.00 | $80.00 |
| **#10**| 08/11/2026 | `PAYMENT` | Pago de compra CCF-4522 a Insumos Pro en efectivo desde Caja General (`$101.70`). | $101.70 | $101.70 |
| **TOTAL** | — | — | **Sumas Iguales de Comprobación Noviembre 2026** | **$11,607.20** | **$11,607.20** |

---

## 7. PREGUNTAS FRECUENTES Y RESOLUCIÓN DE INCIDENCIAS (FAQ)

### P1: ¿Por qué el botón "Cerrar Período" aparece deshabilitado?
**Respuesta:** El sistema cuenta con un validador de pre-cierre estricto. El botón se bloqueará si:
1. Hay al menos una partida en estado Borrador (`DRAFT`). Debe mayorizarla (`POST`) o eliminarla.
2. La suma del Debe no es exactamente igual a la suma del Haber.
3. Existen ventas o compras guardadas que carecen de partida contable vinculada.
4. La sumatoria del Kárdex de existencias no coincide al centavo con el saldo de las cuentas `110401` o `110402`.

### P2: ¿Cómo corregir un documento de venta emitido por error?
**Respuesta:** De acuerdo con la normativa tributaria salvadoreña, los comprobantes fiscales correlativos no se eliminan físicamente. Ingrese al Libro de Ventas, ubique el documento y presione **"Anular"**. El sistema requerirá el motivo de la anulación, marcará el comprobante como `VOIDED` y emitirá automáticamente una **partida contable de reversión** en el Libro Diario para restituir el inventario de Vitrina y neutralizar el IVA Débito Fiscal.

### P3: ¿Por qué no puedo ingresar un precio de venta al crear un insumo de Cabina?
**Respuesta:** Cumpliendo la **Regla de Negocio RN-07**, los insumos de cabina son consumibles técnicos para los estilistas y su costo se amortiza en el servicio prestado; no tienen precio de venta al público. La interfaz oculta y deshabilita este campo, y la base de datos rechaza cualquier registro con `sale_price` no nulo.

### P4: ¿Cómo puedo restablecer los datos de prueba del sistema?
**Respuesta:** En caso de que se hayan realizado pruebas y se desee volver al escenario limpio oficial de Noviembre 2026 con las 82 cuentas cuadradas, abra una terminal y ejecute el siguiente comando de Django:
```bash
docker compose exec -T backend python manage.py seed_mock_data --reset
```
El comando limpiará los movimientos de prueba, cargará las 82 cuentas de la Tabla 1, reinicializará los productos, emitirá las 10 partidas balanceadas y dejará el período de Noviembre 2026 100% listo para cerrar.

---
*Manual elaborado para Diamond Salón Atelier Contable · Noviembre 2026.*
