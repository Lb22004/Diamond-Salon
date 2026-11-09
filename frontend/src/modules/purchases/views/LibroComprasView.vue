<template>
  <div class="ds-page">
    <!-- Top Dark-Gold Responsibility Ribbon (Mock-up Exact) -->
    <div class="ds-vista-ribbon ds-vista-ribbon--dark-gold">
      <div class="ds-vista-ribbon__left">
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <path d="m9 12 2 2 4-4" />
        </svg>
        <span>VISTA 4 · LIBRO DE COMPRAS</span>
        <span class="ds-vista-ribbon__sep">|</span>
        <span>RESPONSABLE: VÍCTOR (JEFE DE COMPRAS &amp; ALMACÉN)</span>
      </div>
      <div class="ds-vista-ribbon__right">
        <span style="text-transform: none; font-weight: 500; opacity: 0.9">Estatus:</span>
        <strong>Libro Cuadrado &amp; Auditado</strong>
        <span class="ds-vista-ribbon__dot" style="background: #f5d48f"></span>
      </div>
    </div>

    <!-- Header Section -->
    <div class="ds-page-header" style="align-items: flex-end; margin-top: 0.25rem">
      <div>
        <div class="ds-subdiario-bar">
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--gold)"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z" />
            <path d="M14 8H8" />
            <path d="M16 12H8" />
            <path d="M13 16H8" />
          </svg>
          <span style="font-weight: 700; letter-spacing: 0.06em; color: var(--gold); text-transform: uppercase">
            CONTROL FISCAL DE ADQUISICIONES
          </span>
        </div>
        <h1 class="ds-serif-title">Libro de compras</h1>
        <p class="ds-serif-subtitle">
          Registro de compras a proveedores e insumos para Diamond Salon
        </p>
      </div>

      <div class="ds-header-actions-row">
        <button type="button" class="ds-btn ds-btn--outline" @click="showSuppliersModal = true">
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
            <path d="M16 3.13a4 4 0 0 1 0 7.75" />
          </svg>
          <span>Proveedores ({{ book.kpis.active_suppliers_count }})</span>
        </button>

        <button type="button" class="ds-btn ds-btn--outline" @click="showWithholdingsModal = true">
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="9" y1="15" x2="15" y2="15" />
          </svg>
          <span>Ver Retenciones IVA</span>
        </button>

        <button type="button" class="ds-btn ds-btn--primary" @click="openCreatePurchaseModal">
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M8 12h8" />
            <path d="M12 8v8" />
          </svg>
          <span>+ Registrar compra</span>
        </button>
      </div>
    </div>

    <div v-if="feedbackMsg" class="ds-alert ds-alert--success">
      {{ feedbackMsg }}
    </div>
    <div v-if="errorMsg" class="ds-alert ds-alert--danger">
      {{ errorMsg }}
    </div>

    <!-- 4 KPI Cards Row (Unified with .ds-sales-kpi-card) -->
    <div class="ds-sales-kpi-grid">
      <!-- Card 1: Total Compras -->
      <div class="ds-sales-kpi-card ds-sales-kpi-card--wine">
        <div class="ds-sales-kpi-card__top">
          <span class="ds-sales-kpi-card__label">TOTAL COMPRAS</span>
          <span class="ds-sales-kpi-card__icon ds-sales-kpi-card__icon--wine" aria-hidden="true">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <rect x="2" y="6" width="20" height="12" rx="2" />
              <circle cx="12" cy="12" r="2" />
              <path d="M6 12h.01M18 12h.01" />
            </svg>
          </span>
        </div>
        <div class="ds-sales-kpi-card__mid">
          <span class="ds-sales-kpi-card__number ds-sales-kpi-card__number--wine">
            ${{ book.kpis.total_purchases }}
          </span>
        </div>
        <div class="ds-sales-kpi-card__foot" style="display: flex; justify-content: space-between">
          <span>Mes Corriente</span>
          <strong style="color: var(--ink)">100% CCF Liquidado</strong>
        </div>
      </div>

      <!-- Card 2: Base Gravada -->
      <div class="ds-sales-kpi-card ds-sales-kpi-card--gold">
        <div class="ds-sales-kpi-card__top">
          <span class="ds-sales-kpi-card__label">BASE GRAVADA</span>
          <span class="ds-sales-kpi-card__icon ds-sales-kpi-card__icon--gold" aria-hidden="true">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <rect x="4" y="2" width="16" height="20" rx="2" />
              <line x1="8" y1="6" x2="16" y2="6" />
              <line x1="16" y1="14" x2="16" y2="18" />
              <path d="M16 10h.01M12 10h.01M8 10h.01M12 14h.01M8 14h.01M12 18h.01M8 18h.01" />
            </svg>
          </span>
        </div>
        <div class="ds-sales-kpi-card__mid">
          <span class="ds-sales-kpi-card__number">${{ book.kpis.taxable_base }}</span>
        </div>
        <div class="ds-sales-kpi-card__foot">
          Costo Directo <strong style="color: var(--ink)">Subtotal Neto</strong>
        </div>
      </div>

      <!-- Card 3: IVA Crédito Fiscal -->
      <div class="ds-sales-kpi-card ds-sales-kpi-card--gold">
        <div class="ds-sales-kpi-card__top">
          <span class="ds-sales-kpi-card__label">IVA CRÉDITO FISCAL</span>
          <span class="ds-sales-kpi-card__icon ds-sales-kpi-card__icon--gold" aria-hidden="true">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <line x1="3" y1="22" x2="21" y2="22" />
              <line x1="6" y1="18" x2="6" y2="11" />
              <line x1="10" y1="18" x2="10" y2="11" />
              <line x1="14" y1="18" x2="14" y2="11" />
              <line x1="18" y1="18" x2="18" y2="11" />
              <polygon points="12 2 20 7 4 7" />
            </svg>
          </span>
        </div>
        <div class="ds-sales-kpi-card__mid">
          <span class="ds-sales-kpi-card__number" style="color: var(--gold)">
            ${{ book.kpis.iva_credit }}
          </span>
        </div>
        <div class="ds-sales-kpi-card__foot" style="display: flex; justify-content: space-between">
          <span>Tasa Vigente 13%</span>
          <strong style="color: var(--gold)">Deducible Fiscal</strong>
        </div>
      </div>

      <!-- Card 4: Proveedores Activos -->
      <div class="ds-sales-kpi-card ds-sales-kpi-card--ink">
        <div class="ds-sales-kpi-card__top">
          <span class="ds-sales-kpi-card__label">PROVEEDORES ACTIVOS</span>
          <span class="ds-sales-kpi-card__icon" style="background: #1b1a19; color: #f5d48f" aria-hidden="true">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="m2 7 4.41-4.41A2 2 0 0 1 7.83 2h8.34a2 2 0 0 1 1.42.59L22 7" />
              <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
              <path d="M15 22v-4a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2v4" />
              <path d="M2 7h20" />
            </svg>
          </span>
        </div>
        <div class="ds-sales-kpi-card__mid" style="justify-content: flex-start; gap: 0.4rem">
          <span class="ds-sales-kpi-card__number">{{ book.kpis.active_suppliers_count }}</span>
          <span style="font-size: 0.78rem; color: var(--ink-muted)">emisores registrados</span>
        </div>
        <div class="ds-sales-kpi-card__foot">
          {{ book.kpis.active_suppliers_names }}
        </div>
      </div>
    </div>

    <!-- Main 2-Column Layout: Left Table Card + Right Distribution & Certification Sidebar -->
    <div class="ds-purchases-layout">
      <!-- LEFT COLUMN: Main Purchase Book Card -->
      <div class="ds-sales-main-card">
        <!-- Filter Toolbar Row 1 -->
        <div class="ds-sales-toolbar-row1">
          <div class="ds-sales-toolbar-left">
            <!-- Period Indicator -->
            <div class="ds-range-pill">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#8a6a1f"
                stroke-width="1.9"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
              </svg>
              <span>PERIODO: <strong>{{ book.period.label }}</strong></span>
            </div>

            <!-- Supplier Filter Select -->
            <select
              v-model="filterSupplier"
              class="ds-range-pill"
              style="padding-right: 1.5rem"
              @change="fetchPurchaseBook"
            >
              <option value="">Todos los Proveedores</option>
              <option v-for="sup in suppliers" :key="sup.id" :value="sup.id">
                {{ sup.name }}
              </option>
            </select>

            <!-- Destination Filter Select -->
            <select
              v-model="filterDestination"
              class="ds-range-pill"
              style="padding-right: 1.5rem"
              @change="fetchPurchaseBook"
            >
              <option value="">Destino: Vitrina &amp; Cabina</option>
              <option value="VITRINA">Solo Vitrina (Reventa · 110401)</option>
              <option value="CABINA">Solo Cabina (Servicio · 110402)</option>
            </select>
          </div>

          <!-- Right Actions: Search + Export + Print -->
          <div class="ds-sales-toolbar-row2">
            <div class="ds-compact-search" style="width: 220px">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#948e84"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.3-4.3" />
              </svg>
              <input
                v-model="searchQuery"
                type="text"
                placeholder="Buscar CCF o proveedor..."
                @input="fetchPurchaseBook"
              />
            </div>

            <ExportButton endpoint="/exports/purchases/" label="Exportar" />

            <button
              type="button"
              class="ds-icon-square-btn"
              title="Imprimir libro de compras"
              @click="handlePrint"
            >
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <polyline points="6 9 6 2 18 2 18 9" />
                <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
                <rect x="6" y="14" width="12" height="8" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Dark Header Table (#1b1a19) -->
        <div style="overflow-x: auto">
          <table class="ds-dark-table">
            <thead>
              <tr>
                <th>FECHA</th>
                <th>DOCUMENTO</th>
                <th>PROVEEDOR</th>
                <th>DESTINO</th>
                <th class="text-right">GRAVADO ($)</th>
                <th class="text-right">IVA ($)</th>
                <th class="text-right">TOTAL ($)</th>
                <th class="text-right">AUDITORÍA</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!book.purchases.length">
                <td colspan="8" class="ds-table__state">
                  No se encontraron comprobantes de compra para el filtro seleccionado.
                </td>
              </tr>
              <tr
                v-for="row in book.purchases"
                :key="row.id"
                :style="row.status === 'VOIDED' ? 'opacity: 0.55; text-decoration: line-through' : ''"
              >
                <td class="mono">{{ formatDateShort(row.doc_date) }}</td>
                <td>
                  <span class="ds-doc-pill">{{ row.doc_number }}</span>
                </td>
                <td>
                  <div style="display: flex; align-items: baseline; gap: 0.45rem; flex-wrap: wrap">
                    <strong style="color: var(--ink)">{{ row.supplier_name }}</strong>
                    <span v-if="row.supplier_brands" style="font-size: 0.76rem; color: var(--ink-muted)">
                      ({{ row.supplier_brands }})
                    </span>
                  </div>
                </td>
                <td>
                  <span
                    v-if="row.destination === 'VITRINA'"
                    class="ds-inv-badge-venta"
                  >
                    Vitrina
                  </span>
                  <span
                    v-else
                    class="ds-inv-badge-servicio"
                  >
                    Cabina
                  </span>
                </td>
                <td class="text-right mono">{{ row.taxable_amount }}</td>
                <td class="text-right mono" style="color: #7c5c13; font-weight: 600">
                  {{ row.iva_credit }}
                </td>
                <td class="text-right mono font-bold">{{ row.total }}</td>
                <td class="text-right">
                  <div class="ds-row-actions" style="justify-content: flex-end">
                    <router-link
                      v-if="row.journal_entry_number"
                      :to="`/libro-diario?entry=${row.journal_entry_id}`"
                      class="ds-account-link mono"
                      title="Ver partida contable en Libro Diario"
                    >
                      #{{ row.journal_entry_number }}
                    </router-link>
                    <button
                      v-if="row.status === 'REGISTERED' && row.payment_status !== 'PAID'"
                      type="button"
                      class="ds-btn ds-btn--outline ds-btn--sm"
                      title="Registrar abono o liquidación a proveedor"
                      @click="openPaymentModal(row)"
                    >
                      Pagar
                    </button>
                    <span
                      v-else-if="row.payment_status === 'PAID'"
                      class="ds-sales-kpi-card__pill ds-sales-kpi-card__pill--gold"
                    >
                      Pagado
                    </span>
                    <button
                      v-if="row.status === 'REGISTERED'"
                      type="button"
                      class="ds-btn-link"
                      style="font-size: 0.74rem; color: var(--danger)"
                      @click="openVoidModal(row)"
                    >
                      Anular
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <td colspan="4" style="font-size: 0.92rem">Totales del periodo</td>
                <td class="text-right mono">{{ book.totals.taxable_amount }}</td>
                <td class="text-right mono" style="color: #8a6a1f">{{ book.totals.iva_credit }}</td>
                <td class="text-right mono" style="color: var(--wine)">{{ book.totals.total }}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>

        <!-- Audit Note Bar inside Card -->
        <div class="ds-audit-note-bar">
          <div class="ds-audit-note-bar__text">
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              style="flex-shrink: 0; margin-top: 2px"
            >
              <circle cx="12" cy="12" r="10" />
              <path d="M12 16v-4" />
              <path d="M12 8h.01" />
            </svg>
            <span>
              Al comprar se indica el destino (vitrina o cabina). Con eso el producto entra al
              inventario correcto automáticamente.
            </span>
          </div>
        </div>
      </div>

      <!-- RIGHT COLUMN: Distribution by Destination + Fiscal Certification Card -->
      <aside class="ds-purchases-sidebar">
        <!-- Card 1: Distribución por Destino -->
        <div class="ds-dist-card">
          <div style="display: flex; align-items: center; justify-content: space-between">
            <span class="ds-sales-kpi-card__label">DISTRIBUCIÓN POR DESTINO</span>
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#8a6a1f"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M21.21 15.89A10 10 0 1 1 8 2.83" />
              <path d="M22 12A10 10 0 0 0 12 2v10z" />
            </svg>
          </div>
          <h3 style="margin: 0; font-family: Georgia, serif; font-size: 1.15rem">
            Asignación de Inversión
          </h3>

          <!-- Dual Progress Bar -->
          <div class="ds-dist-bar">
            <div
              class="ds-dist-bar__vitrina"
              :style="{ width: `${book.distribution.vitrina_pct}%` }"
            ></div>
            <div
              class="ds-dist-bar__cabina"
              :style="{ width: `${book.distribution.cabina_pct}%` }"
            ></div>
          </div>

          <div class="ds-dist-row">
            <div class="ds-dist-row__left">
              <span class="ds-dist-dot ds-dist-dot--wine"></span>
              <span>Vitrina (Reventa)</span>
            </div>
            <strong class="mono" style="color: var(--wine)">
              ${{ book.distribution.vitrina_amount }} ({{ book.distribution.vitrina_pct }}%)
            </strong>
          </div>

          <div class="ds-dist-row">
            <div class="ds-dist-row__left">
              <span class="ds-dist-dot ds-dist-dot--ink"></span>
              <span>Cabina (Servicio)</span>
            </div>
            <strong class="mono">
              ${{ book.distribution.cabina_amount }} ({{ book.distribution.cabina_pct }}%)
            </strong>
          </div>

          <p style="margin: 0; font-size: 0.75rem; color: var(--ink-muted); line-height: 1.48">
            Las compras clasificadas en <strong>Cabina</strong> se cargan directamente a la cuenta
            contable <em>Costo de Servicios Atelier</em> al consumirse en tocador.
          </p>
        </div>

        <!-- Card 2: Certificación Fiscal · Comprobantes CCF Válidos -->
        <div class="ds-cert-card">
          <div class="ds-cert-card__head">
            <span class="ds-cert-card__icon" aria-hidden="true">
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M9 11l3 3L22 4" />
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
              </svg>
            </span>
            <div>
              <div class="ds-cert-card__eyebrow">CERTIFICACIÓN FISCAL</div>
              <h4 class="ds-cert-card__title">Comprobantes CCF Válidos</h4>
            </div>
          </div>

          <p class="ds-cert-card__body">
            Todos los créditos fiscales del período han sido cotejados con el número de registro
            tributario de los proveedores autorizados.
          </p>

          <div class="ds-cert-card__foot">
            <span>Última auditoría: Hoy, 09:30 AM</span>
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
          </div>
        </div>
      </aside>
    </div>

    <!-- Bottom 3 Supplier Highlight Cards (Mock-up Exact) -->
    <div class="ds-supplier-cards-grid">
      <div
        class="ds-supplier-highlight-card"
        @click="filterByDestination('VITRINA')"
      >
        <div class="ds-supplier-highlight-card__thumb ds-supplier-highlight-card__thumb--wine">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" />
            <path d="M3 6h18" />
            <path d="M16 10a4 4 0 0 1-8 0" />
          </svg>
        </div>
        <div>
          <div class="ds-supplier-highlight-card__eyebrow ds-supplier-highlight-card__eyebrow--wine">
            DESTINO VITRINA
          </div>
          <h4 class="ds-supplier-highlight-card__name">Distribuidora Bella</h4>
          <p class="ds-supplier-highlight-card__desc">
            Lote ingresado con código de barras de venta directa.
          </p>
        </div>
      </div>

      <div
        class="ds-supplier-highlight-card"
        @click="filterByDestination('CABINA')"
      >
        <div class="ds-supplier-highlight-card__thumb">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M10 2v7.31" />
            <path d="M14 9.3V1.99" />
            <path d="M8.5 2h7" />
            <path d="M14 9.3a6.5 6.5 0 1 1-4 0" />
            <path d="M5.52 16h12.96" />
          </svg>
        </div>
        <div>
          <div class="ds-supplier-highlight-card__eyebrow">DESTINO CABINA</div>
          <h4 class="ds-supplier-highlight-card__name">Insumos Pro</h4>
          <p class="ds-supplier-highlight-card__desc">
            Reactivos químicos de formulación profesional para estilistas.
          </p>
        </div>
      </div>

      <div
        class="ds-supplier-highlight-card"
        @click="filterByDestination('CABINA')"
      >
        <div class="ds-supplier-highlight-card__thumb">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z" />
          </svg>
        </div>
        <div>
          <div class="ds-supplier-highlight-card__eyebrow">DESTINO CABINA</div>
          <h4 class="ds-supplier-highlight-card__name">Color &amp; Style</h4>
          <p class="ds-supplier-highlight-card__desc">
            Gama de tintes sin amoniaco recién transferida a estaciones.
          </p>
        </div>
      </div>
    </div>

    <!-- MODAL 1: + Registrar Compra (RF-COM-02..04) -->
    <ModalDialog
      v-model="showCreateModal"
      title="Registrar Comprobante de Compra (CCF)"
      subtitle="Ingresa existencias al Kárdex, recalcula el costo promedio ponderado y contabiliza la partida doble."
      size="lg"
    >
      <form class="flex-col gap-md" @submit.prevent="submitPurchase">
        <div class="ds-form-grid">
          <div class="ds-field">
            <label class="ds-field__label">Proveedor Autorizado *</label>
            <select v-model="purchaseForm.supplier_id" class="ds-input" required>
              <option v-for="sup in suppliers" :key="sup.id" :value="sup.id">
                {{ sup.name }} (NRC: {{ sup.nrc || 'S/N' }})
              </option>
            </select>
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Tipo de Comprobante *</label>
            <select v-model="purchaseForm.doc_type" class="ds-input" required>
              <option value="CCF">Comprobante de Crédito Fiscal (CCF 13%)</option>
              <option value="INVOICE">Factura de Consumidor Final</option>
            </select>
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Número de Documento *</label>
            <input
              v-model="purchaseForm.doc_number"
              type="text"
              class="ds-input"
              placeholder="Ej. CCF-4535"
              required
            />
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Fecha de Emisión *</label>
            <input v-model="purchaseForm.doc_date" type="date" class="ds-input" required />
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Destino Contable (RN-07) *</label>
            <select
              v-model="purchaseForm.destination"
              class="ds-input"
              required
              @change="syncProductForDestination"
            >
              <option value="VITRINA">Vitrina · Reventa Comercial (Cuenta 110401)</option>
              <option value="CABINA">Cabina · Insumo de Servicio (Cuenta 110402)</option>
            </select>
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Condición de Pago *</label>
            <select v-model="purchaseForm.payment_condition" class="ds-input" required>
              <option value="CREDIT">Crédito (210101 Cuentas por Pagar Proveedores)</option>
              <option value="CASH">Contado (110101 Caja General)</option>
            </select>
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Artículo de Inventario ({{ purchaseForm.destination }}) *</label>
            <select v-model="purchaseForm.product_id" class="ds-input" required>
              <option v-for="prod in filteredProductsByDest" :key="prod.id" :value="prod.id">
                {{ prod.sku }} · {{ prod.name }}
              </option>
            </select>
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Cantidad Comprada *</label>
            <input
              v-model="purchaseForm.quantity"
              type="number"
              step="0.01"
              min="0.01"
              class="ds-input"
              required
            />
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Costo Unitario Neto ($ sin IVA) *</label>
            <input
              v-model="purchaseForm.unit_cost"
              type="number"
              step="0.01"
              min="0.01"
              class="ds-input"
              required
            />
          </div>
        </div>

        <div class="ds-inv-kpi-footbox">
          <span>Base Gravada: <strong>${{ previewSubtotal }}</strong></span>
          <span>IVA Crédito Fiscal (13%): <strong>${{ previewIva }}</strong></span>
          <span>Total CCF: <strong>${{ previewTotal }}</strong></span>
        </div>

        <div class="ds-modal__footer" style="padding: 0.75rem 0 0; background: transparent">
          <button type="button" class="ds-btn ds-btn--outline" @click="showCreateModal = false">
            Cancelar
          </button>
          <button type="submit" class="ds-btn ds-btn--primary" :disabled="submitting">
            {{ submitting ? 'Contabilizando...' : 'Registrar compra y mayorizar' }}
          </button>
        </div>
      </form>
    </ModalDialog>

    <!-- MODAL 2: Ver Retenciones y Percepciones IVA (RF-COM-10) -->
    <ModalDialog
      v-model="showWithholdingsModal"
      title="Resumen de Créditos, Percepciones y Retenciones de IVA"
      subtitle="Control auxiliar de impuestos acreditables para declaración mensual F-07."
      size="md"
    >
      <div class="flex-col gap-md">
        <div class="ds-dist-row">
          <span>IVA Crédito Fiscal sobre compras (13% — Cuenta 110401)</span>
          <strong class="mono">${{ book.withholdings.iva_credit_13 }}</strong>
        </div>
        <div class="ds-dist-row">
          <span>IVA Percibido 1% por Grandes Contribuyentes (Cuenta 110402)</span>
          <strong class="mono">${{ book.withholdings.iva_perceived_1 }}</strong>
        </div>
        <div class="ds-dist-row">
          <span>IVA Retenido 1% en ventas CCF a Grandes Contribuyentes</span>
          <strong class="mono">${{ book.withholdings.iva_withheld_sales_1 }}</strong>
        </div>
        <div class="ds-inv-kpi-footbox ds-inv-kpi-footbox--gold">
          <span>TOTAL CRÉDITO Y RETENCIONES ACREDITABLES DEL PERÍODO</span>
          <strong>${{ book.withholdings.total_acreditable }}</strong>
        </div>
      </div>
    </ModalDialog>

    <!-- MODAL 3: Catálogo de Proveedores (RF-COM-01) -->
    <ModalDialog
      v-model="showSuppliersModal"
      title="Catálogo de Proveedores Autorizados"
      subtitle="Emisores de Comprobantes de Crédito Fiscal (CCF) registrados en el atelier."
      size="lg"
    >
      <div class="flex-col gap-md">
        <table class="ds-dark-table">
          <thead>
            <tr>
              <th>PROVEEDOR</th>
              <th>LÍNEAS / MARCAS</th>
              <th>NIT</th>
              <th>NRC</th>
              <th>CATEGORÍA</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="sup in suppliers" :key="sup.id">
              <td><strong>{{ sup.name }}</strong></td>
              <td>{{ sup.brands_description || '—' }}</td>
              <td class="mono">{{ sup.nit }}</td>
              <td class="mono">{{ sup.nrc || '—' }}</td>
              <td>{{ sup.taxpayer_category }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </ModalDialog>

    <!-- MODAL 4: Registrar Pago a Proveedor (RF-COM-09) -->
    <ModalDialog
      v-model="showPaymentModal"
      :title="selectedPurchase ? `Liquidar Cuenta por Pagar · ${selectedPurchase.doc_number}` : 'Pago a Proveedor'"
      subtitle="Contabiliza automáticamente Debe 210101 Proveedores / Haber 110101 Caja o 110102 Bancos."
      size="md"
    >
      <form v-if="selectedPurchase" class="flex-col gap-md" @submit.prevent="submitPayment">
        <div class="ds-form-grid">
          <div class="ds-field">
            <label class="ds-field__label">Fecha de Pago *</label>
            <input v-model="paymentForm.payment_date" type="date" class="ds-input" required />
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Monto a Pagar ($) *</label>
            <input
              v-model="paymentForm.amount"
              type="number"
              step="0.01"
              min="0.01"
              :max="selectedPurchase.balance_due"
              class="ds-input"
              required
            />
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Medio de Egreso *</label>
            <select v-model="paymentForm.payment_method" class="ds-input" required>
              <option value="CASH">Efectivo (110101 Caja General)</option>
              <option value="TRANSFER">Transferencia Bancaria (110102 Bancos)</option>
            </select>
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Referencia / Comprobante</label>
            <input
              v-model="paymentForm.reference"
              type="text"
              class="ds-input"
              placeholder="Ej. TRF-8821"
            />
          </div>
        </div>
        <div class="ds-modal__footer" style="padding: 0.75rem 0 0; background: transparent">
          <button type="button" class="ds-btn ds-btn--outline" @click="showPaymentModal = false">
            Cancelar
          </button>
          <button type="submit" class="ds-btn ds-btn--primary" :disabled="submitting">
            {{ submitting ? 'Procesando...' : 'Registrar pago y mayorizar' }}
          </button>
        </div>
      </form>
    </ModalDialog>

    <!-- MODAL 5: Anular Compra (RF-COM-11) -->
    <ModalDialog
      v-model="showVoidModal"
      :title="selectedPurchase ? `Anular Comprobante ${selectedPurchase.doc_number}` : 'Anular Compra'"
      subtitle="Revierte la entrada en el Kárdex y genera la partida de reversión en el Libro Diario."
      size="sm"
    >
      <form v-if="selectedPurchase" class="flex-col gap-md" @submit.prevent="submitVoid">
        <div class="ds-field">
          <label class="ds-field__label">Motivo de Anulación Fiscal *</label>
          <input
            v-model="voidReason"
            type="text"
            class="ds-input"
            placeholder="Ej. Error en digitación de correlativo CCF"
            required
          />
        </div>
        <div class="ds-modal__footer" style="padding: 0.75rem 0 0; background: transparent">
          <button type="button" class="ds-btn ds-btn--outline" @click="showVoidModal = false">
            Cancelar
          </button>
          <button type="submit" class="ds-btn ds-btn--primary" :disabled="submitting">
            {{ submitting ? 'Anulando...' : 'Confirmar anulación' }}
          </button>
        </div>
      </form>
    </ModalDialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import client from '@/api/http'
import { usePeriodStore } from '@/stores/period'
import { ExportButton, FormModal as ModalDialog } from '@/components/ui'

const periodStore = usePeriodStore()
const filterSupplier = ref('')
const filterDestination = ref('')
const searchQuery = ref('')
const submitting = ref(false)
const feedbackMsg = ref('')
const errorMsg = ref('')

const suppliers = ref([])
const products = ref([])

const book = ref({
  period: { id: null, label: 'Noviembre 2026' },
  kpis: {
    total_purchases: '339.00',
    taxable_base: '300.00',
    iva_credit: '39.00',
    iva_perceived: '0.00',
    active_suppliers_count: 3,
    active_suppliers_names: 'Distribuidora Bella, Insumos Pro, Color & Style',
    documents_count: 3,
  },
  distribution: {
    vitrina_amount: '169.50',
    vitrina_pct: 50,
    cabina_amount: '169.50',
    cabina_pct: 50,
  },
  purchases: [],
  totals: {
    taxable_amount: '300.00',
    exempt_amount: '0.00',
    iva_credit: '39.00',
    iva_perceived: '0.00',
    total: '339.00',
  },
  withholdings: {
    iva_credit_13: '39.00',
    iva_perceived_1: '0.00',
    iva_withheld_sales_1: '0.00',
    total_acreditable: '39.00',
  },
})

const showCreateModal = ref(false)
const showWithholdingsModal = ref(false)
const showSuppliersModal = ref(false)
const showPaymentModal = ref(false)
const showVoidModal = ref(false)
const selectedPurchase = ref(null)
const voidReason = ref('')

const purchaseForm = ref({
  supplier_id: null,
  doc_type: 'CCF',
  doc_number: '',
  doc_date: '2026-11-05',
  destination: 'VITRINA',
  payment_condition: 'CREDIT',
  product_id: null,
  quantity: '5',
  unit_cost: '10.00',
})

const paymentForm = ref({
  payment_date: '2026-11-10',
  amount: '0.00',
  payment_method: 'CASH',
  reference: '',
})

const filteredProductsByDest = computed(() =>
  products.value.filter((p) => p.inventory_type === purchaseForm.value.destination),
)

const previewSubtotal = computed(() => {
  const q = parseFloat(purchaseForm.value.quantity || 0)
  const c = parseFloat(purchaseForm.value.unit_cost || 0)
  return (q * c).toFixed(2)
})

const previewIva = computed(() => {
  if (purchaseForm.value.doc_type !== 'CCF') return '0.00'
  return (parseFloat(previewSubtotal.value) * 0.13).toFixed(2)
})

const previewTotal = computed(() =>
  (parseFloat(previewSubtotal.value) + parseFloat(previewIva.value)).toFixed(2),
)

async function fetchCatalogs() {
  try {
    const [supResp, prodResp] = await Promise.all([
      client.get('/purchases/suppliers/'),
      client.get('/inventory/products/'),
    ])
    suppliers.value = supResp.data.results || supResp.data
    products.value = prodResp.data.results || prodResp.data
  } catch {
    // Non-fatal
  }
}

async function fetchPurchaseBook() {
  try {
    const { data } = await client.get('/purchases/purchase-book/', {
      params: {
        period: periodStore.selectedPeriodId || undefined,
        supplier: filterSupplier.value || undefined,
        destination: filterDestination.value || undefined,
        search: searchQuery.value || undefined,
      },
    })
    book.value = data
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'No se pudo cargar el Libro de Compras.'
  }
}

function syncProductForDestination() {
  if (filteredProductsByDest.value.length) {
    purchaseForm.value.product_id = filteredProductsByDest.value[0].id
  }
}

function openCreatePurchaseModal() {
  feedbackMsg.value = ''
  errorMsg.value = ''
  purchaseForm.value = {
    supplier_id: suppliers.value[0]?.id || null,
    doc_type: 'CCF',
    doc_number: `CCF-45${31 + book.value.purchases.length}`,
    doc_date: '2026-11-06',
    destination: 'VITRINA',
    payment_condition: 'CREDIT',
    product_id: null,
    quantity: '5',
    unit_cost: '10.00',
  }
  syncProductForDestination()
  showCreateModal.value = true
}

function openPaymentModal(row) {
  feedbackMsg.value = ''
  errorMsg.value = ''
  selectedPurchase.value = row
  paymentForm.value = {
    payment_date: '2026-11-10',
    amount: row.balance_due,
    payment_method: 'CASH',
    reference: `Abono ${row.doc_number}`,
  }
  showPaymentModal.value = true
}

function openVoidModal(row) {
  feedbackMsg.value = ''
  errorMsg.value = ''
  selectedPurchase.value = row
  voidReason.value = ''
  showVoidModal.value = true
}

async function submitPurchase() {
  feedbackMsg.value = ''
  errorMsg.value = ''
  submitting.value = true
  try {
    const { data } = await client.post('/purchases/purchases/', {
      supplier_id: purchaseForm.value.supplier_id,
      doc_type: purchaseForm.value.doc_type,
      doc_number: purchaseForm.value.doc_number,
      doc_date: purchaseForm.value.doc_date,
      destination: purchaseForm.value.destination,
      payment_condition: purchaseForm.value.payment_condition,
      lines: [
        {
          product_id: purchaseForm.value.product_id,
          quantity: purchaseForm.value.quantity,
          unit_cost: purchaseForm.value.unit_cost,
        },
      ],
    })
    showCreateModal.value = false
    feedbackMsg.value = `Compra ${data.doc_number} registrada en Kárdex y mayorizada en Partida #${data.journal_entry_number || data.id}.`
    await fetchPurchaseBook()
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Error al registrar la compra.'
  } finally {
    submitting.value = false
  }
}

async function submitPayment() {
  if (!selectedPurchase.value) return
  feedbackMsg.value = ''
  errorMsg.value = ''
  submitting.value = true
  try {
    const { data } = await client.post(
      `/purchases/purchases/${selectedPurchase.value.id}/payments/`,
      paymentForm.value,
    )
    showPaymentModal.value = false
    feedbackMsg.value = `Pago aplicado y mayorizado en Partida #${data.journal_entry_number || data.id}.`
    await fetchPurchaseBook()
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Error al registrar el pago al proveedor.'
  } finally {
    submitting.value = false
  }
}

async function submitVoid() {
  if (!selectedPurchase.value) return
  feedbackMsg.value = ''
  errorMsg.value = ''
  submitting.value = true
  try {
    await client.post(`/purchases/purchases/${selectedPurchase.value.id}/void/`, {
      reason: voidReason.value,
    })
    showVoidModal.value = false
    feedbackMsg.value = `Comprobante ${selectedPurchase.value.doc_number} anulado y revertido del Kárdex.`
    await fetchPurchaseBook()
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'No se pudo anular la compra.'
  } finally {
    submitting.value = false
  }
}

function filterByDestination(dest) {
  filterDestination.value = filterDestination.value === dest ? '' : dest
  fetchPurchaseBook()
}

function formatDateShort(iso) {
  if (!iso) return ''
  const [y, m, d] = iso.slice(0, 10).split('-')
  return `${d}/${m}/${y.slice(2)}`
}

function handlePrint() {
  window.print()
}

watch(
  () => periodStore.selectedPeriodId,
  () => {
    fetchPurchaseBook()
  },
)

onMounted(async () => {
  await Promise.all([fetchCatalogs(), fetchPurchaseBook()])
})
</script>
