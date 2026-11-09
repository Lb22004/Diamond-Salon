<template>
  <section class="ds-page">
    <!-- Top Amber Ribbon Banner -->
    <div class="ds-vista-ribbon">
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
          aria-hidden="true"
        >
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <polyline points="9 12 11 14 15 10" />
        </svg>
        <span>VISTA 3 · LIBRO DE VENTAS · EJERCICIO FISCAL {{ periodStore.activePeriod?.year || 2026 }}</span>
      </div>
      <div class="ds-vista-ribbon__right">
        <span class="ds-vista-ribbon__dot"></span>
        <span>RESPONSABLE: VÍCTOR FLORES</span>
        <span class="ds-vista-ribbon__sep">|</span>
        <span>RÉGIMEN GENERAL IVA (13%)</span>
      </div>
    </div>

    <!-- Header Section -->
    <header class="ds-page__header" style="align-items: flex-start">
      <div>
        <div class="ds-subdiario-bar">
          <span class="ds-subdiario-pill">SUBDIARIO FISCAL</span>
          <span>· Periodo contable {{ periodShortRangeLabel }}</span>
        </div>
        <h1 class="ds-serif-title">Libro de ventas</h1>
        <p class="ds-serif-subtitle">
          Registro cronológico y discriminado de ingresos por servicios de belleza y venta directa en vitrina.
        </p>
      </div>

      <div class="ds-header-actions-stack">
        <div class="ds-header-actions-row">
          <button type="button" class="ds-btn ds-btn--outline ds-btn--sm" @click="showServicesModal = true">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="6" cy="6" r="3" />
              <circle cx="6" cy="18" r="3" />
              <line x1="20" y1="4" x2="8.12" y2="15.88" />
              <line x1="14.47" y1="14.48" x2="20" y2="20" />
              <line x1="8.12" y1="8.12" x2="12" y2="12" />
            </svg>
            <span>Servicios ({{ services.length }})</span>
          </button>
          <button type="button" class="ds-btn ds-btn--outline ds-btn--sm" @click="showCustomersModal = true">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
            <span>Clientes ({{ customers.length }})</span>
          </button>
          <ExportButton
            :book="exportBookKey"
            :params="exportParams"
            label="Descargar reporte mensual"
          />
        </div>
        <button
          v-if="canWriteSales"
          type="button"
          class="ds-btn ds-btn--primary"
          style="min-width: 225px; padding: 0.6rem 1.15rem"
          :disabled="!periodStore.isPeriodOpen"
          @click="openNewSaleModal"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="16" />
            <line x1="8" y1="12" x2="16" y2="12" />
          </svg>
          <span>+ Registrar venta</span>
        </button>
      </div>
    </header>

    <!-- 4 KPI Cards — Unified with KpiCard Design System + Clean Vector Icons (RF-VEN-08, OI-6) -->
    <div class="ds-sales-kpi-grid">
      <!-- KPI 1: Ventas Brutas Totales -->
      <article class="ds-sales-kpi-card ds-sales-kpi-card--gold">
        <div class="ds-sales-kpi-card__top">
          <span class="ds-sales-kpi-card__label">VENTAS BRUTAS TOTALES</span>
          <span class="ds-sales-kpi-card__icon ds-sales-kpi-card__icon--gold" aria-hidden="true">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
              <rect x="2" y="6" width="20" height="12" rx="2" />
              <circle cx="12" cy="12" r="2.5" />
              <path d="M6 12h.01M18 12h.01" />
            </svg>
          </span>
        </div>
        <div class="ds-sales-kpi-card__mid">
          <span class="ds-sales-kpi-card__number">{{ formatMoney(salesBook.kpis?.gross_sales || '0.00') }}</span>
          <span class="ds-sales-kpi-card__pill ds-sales-kpi-card__pill--gold">100% Total</span>
        </div>
        <div class="ds-sales-kpi-card__foot">Monto facturado bruto acumulado</div>
      </article>

      <!-- KPI 2: Base Imponible Gravada -->
      <article class="ds-sales-kpi-card ds-sales-kpi-card--ink">
        <div class="ds-sales-kpi-card__top">
          <span class="ds-sales-kpi-card__label">BASE IMPONIBLE GRAVADA</span>
          <span class="ds-sales-kpi-card__icon" aria-hidden="true">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="3" />
              <path d="M15 9.5a3.5 3.5 0 1 0 0 5h-2.5V12" />
            </svg>
          </span>
        </div>
        <div class="ds-sales-kpi-card__mid">
          <span class="ds-sales-kpi-card__number">{{ formatMoney(salesBook.kpis?.taxable_base || '0.00') }}</span>
          <span class="ds-sales-kpi-card__pill ds-sales-kpi-card__pill--neutral">
            {{ salesBook.kpis?.taxable_pct || '88.49%' }}
          </span>
        </div>
        <div class="ds-sales-kpi-card__foot">Ingresos netos del periodo</div>
      </article>

      <!-- KPI 3: IVA Débito Fiscal (13%) -->
      <article class="ds-sales-kpi-card ds-sales-kpi-card--wine">
        <div class="ds-sales-kpi-card__top">
          <span class="ds-sales-kpi-card__label">IVA DÉBITO FISCAL (13%)</span>
          <span class="ds-sales-kpi-card__icon ds-sales-kpi-card__icon--wine" aria-hidden="true">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z" />
              <line x1="8" y1="9" x2="16" y2="9" />
              <line x1="8" y1="13" x2="16" y2="13" />
              <line x1="8" y1="17" x2="12" y2="17" />
            </svg>
          </span>
        </div>
        <div class="ds-sales-kpi-card__mid">
          <span class="ds-sales-kpi-card__number ds-sales-kpi-card__number--wine">
            {{ formatMoney(salesBook.kpis?.iva_debit || '0.00') }}
          </span>
          <span class="ds-sales-kpi-card__pill ds-sales-kpi-card__pill--wine">Crédito por liquidar</span>
        </div>
        <div class="ds-sales-kpi-card__foot">Impuesto retenido a enterar</div>
      </article>

      <!-- KPI 4: Comprobantes Emitidos -->
      <article class="ds-sales-kpi-card ds-sales-kpi-card--gold">
        <div class="ds-sales-kpi-card__top">
          <span class="ds-sales-kpi-card__label">COMPROBANTES EMITIDOS</span>
          <span class="ds-sales-kpi-card__icon ds-sales-kpi-card__icon--gold" aria-hidden="true">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
              <path d="M9 11l3 3L22 4" />
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
          </span>
        </div>
        <div class="ds-sales-kpi-card__mid">
          <span class="ds-sales-kpi-card__number">
            {{ salesBook.kpis?.documents_issued || 0 }}
            <small style="font-size: 0.82rem; font-weight: 600; color: var(--ink-muted)">
              {{ (salesBook.kpis?.ccf_count || 0) > 0 ? 'DOC' : 'FCF' }}
            </small>
          </span>
          <span class="ds-sales-kpi-card__pill ds-sales-kpi-card__pill--gold">Secuencia Activa</span>
        </div>
        <div class="ds-sales-kpi-card__foot">
          {{ salesBook.kpis?.correlative_range || 'Sin emisiones' }}
        </div>
      </article>
    </div>

    <!-- Main White Container Card -->
    <div class="ds-sales-main-card">
      <!-- Toolbar Row 1: Date Range Pill + Segmented Tabs + Status Pill -->
      <div class="ds-sales-toolbar-row1">
        <div class="ds-sales-toolbar-left">
          <button
            type="button"
            class="ds-range-pill"
            @click="showRangeInputs = !showRangeInputs"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" style="color: var(--gold)">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
            <span>RANGO: <strong>{{ formattedRangeDisplay }}</strong></span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="opacity: 0.6">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>

          <!-- Segmented Filter & Legal Book Tabs -->
          <div class="ds-segmented-tabs">
            <button
              type="button"
              class="ds-segmented-tab"
              :class="{ 'is-active': activeBookTab === 'all' && filterLineType === '' }"
              @click="selectMainFilter('all', '')"
            >
              Todos ({{ salesBook.counts?.all || 0 }})
            </button>
            <button
              type="button"
              class="ds-segmented-tab"
              :class="{ 'is-active': activeBookTab === 'all' && filterLineType === 'SERVICE' }"
              @click="selectMainFilter('all', 'SERVICE')"
            >
              Servicio ({{ salesBook.counts?.services || 0 }})
            </button>
            <button
              type="button"
              class="ds-segmented-tab"
              :class="{ 'is-active': activeBookTab === 'all' && filterLineType === 'PRODUCT' }"
              @click="selectMainFilter('all', 'PRODUCT')"
            >
              Venta de producto ({{ salesBook.counts?.products || 0 }})
            </button>
            <button
              type="button"
              class="ds-segmented-tab"
              :class="{ 'is-active': activeBookTab === 'fcf' }"
              @click="activeBookTab = 'fcf'"
            >
              Libro FCF ({{ salesBook.counts?.fcf || 0 }})
            </button>
            <button
              type="button"
              class="ds-segmented-tab"
              :class="{ 'is-active': activeBookTab === 'ccf' }"
              @click="activeBookTab = 'ccf'"
            >
              Libro CCF ({{ salesBook.counts?.ccf || 0 }})
            </button>
          </div>
        </div>

        <div class="ds-status-pill">
          <span class="ds-status-pill__dot"></span>
          <span>Estado: <strong>Registrado y Mayorizado</strong></span>
        </div>
      </div>

      <!-- Optional collapsible date range & doc_type inputs -->
      <div
        v-if="showRangeInputs"
        class="flex-between"
        style="padding: 10px 14px; background: #faf8f4; border: 1px solid #ece7dc; border-radius: 6px; flex-wrap: wrap; gap: 12px"
      >
        <DateRangePicker
          v-model:from="dateFrom"
          v-model:to="dateTo"
          @change="fetchSalesBook"
        />
        <div class="flex-row gap-xs">
          <select v-model="filterDocType" class="ds-input ds-input--sm" style="width: 165px" @change="fetchSalesBook">
            <option value="">Todo Doc. Fiscal</option>
            <option value="FCF">Solo FCF</option>
            <option value="CCF">Solo CCF</option>
            <option value="NC">Notas de Crédito</option>
          </select>
          <button
            type="button"
            class="ds-btn ds-btn--outline ds-btn--sm"
            @click="clearDateFilter"
          >
            Restablecer fechas
          </button>
        </div>
      </div>

      <!-- Toolbar Row 2: Right-aligned compact search & print button -->
      <div class="ds-sales-toolbar-row2">
        <div class="ds-compact-search">
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            style="color: #8c857b; flex-shrink: 0"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Filtrar por cliente o factura..."
            @input="fetchSalesBook"
          />
        </div>
        <button
          type="button"
          class="ds-icon-square-btn"
          title="Imprimir libro de ventas"
          @click="printSalesBook"
        >
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.9"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <polyline points="6 9 6 2 18 2 18 9" />
            <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
            <rect x="6" y="14" width="12" height="8" />
          </svg>
        </button>
      </div>

      <!-- ==================== TAB 1: REGISTRO DETALLADO (DEFAULT MOCK-UP TABLE) ==================== -->
      <template v-if="activeBookTab === 'all'">
        <div style="overflow-x: auto">
          <table class="ds-dark-table">
            <thead>
              <tr>
                <th style="width: 105px">FECHA</th>
                <th style="width: 130px">DOCUMENTO</th>
                <th style="width: 190px">CLIENTE</th>
                <th>CONCEPTO</th>
                <th class="text-right" style="width: 125px">GRAVADO ($)</th>
                <th class="text-right" style="width: 110px">IVA ($)</th>
                <th class="text-right" style="width: 120px">TOTAL ($)</th>
                <th class="text-right" style="width: 110px">AUDITORÍA</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!salesBook.sales?.length">
                <td colspan="8" class="text-center text-muted" style="padding: 36px 20px">
                  No se encontraron comprobantes de venta para el rango o filtro seleccionado.
                </td>
              </tr>

              <tr
                v-for="sale in salesBook.sales"
                :key="sale.id"
                :style="{ opacity: sale.status === 'VOIDED' ? 0.5 : 1 }"
              >
                <td class="mono" style="font-weight: 500; color: #3a3530">
                  {{ formatShortDate(sale.sale_date) }}
                </td>
                <td>
                  <span class="ds-doc-pill" style="cursor: pointer" @click="inspectSale(sale)">
                    {{ sale.doc_number }}
                  </span>
                </td>
                <td>
                  <span
                    v-if="isFinalConsumerName(sale.customer_name)"
                    style="font-style: italic; color: #6f6961; font-family: Georgia, serif; font-size: 14.5px"
                  >
                    {{ sale.customer_name }}
                  </span>
                  <div v-else>
                    <div style="font-weight: 700; color: #1f1d1a">{{ sale.customer_name }}</div>
                    <div v-if="sale.customer_nrc" class="mono text-muted" style="font-size: 10.5px">
                      NRC: {{ sale.customer_nrc }}
                    </div>
                  </div>
                </td>
                <td>
                  <div class="flex-row gap-sm" style="align-items: center">
                    <span
                      class="ds-regime-tag"
                      :class="{
                        'ds-regime-tag--cabina': sale.primary_regime === 'CABINA',
                        'ds-regime-tag--vitrina': sale.primary_regime === 'VITRINA',
                        'ds-regime-tag--mixto': sale.primary_regime === 'MIXTO',
                      }"
                    >
                      {{ sale.primary_regime }}
                    </span>
                    <span style="color: #3a3530; font-size: 13.5px">{{ sale.concept_summary }}</span>
                  </div>
                </td>
                <td class="text-right mono" style="font-weight: 600; color: #1f1d1a">
                  {{ formatRawNumber(sale.taxable_amount) }}
                </td>
                <td class="text-right mono" style="font-weight: 600; color: #8c1d2c">
                  {{ formatRawNumber(sale.iva_amount) }}
                </td>
                <td class="text-right mono" style="font-weight: 800; color: #1b1a19; font-size: 14px">
                  {{ formatRawNumber(sale.total) }}
                </td>
                <td class="text-right">
                  <div class="flex-row gap-xs" style="justify-content: flex-end">
                    <router-link
                      v-if="sale.journal_entry"
                      :to="{ path: '/diario', query: { entry: sale.journal_entry } }"
                      class="mono"
                      style="color: #8a6a1f; font-weight: 700; font-size: 11.5px; text-decoration: none"
                      title="Ver asiento en Libro Diario"
                    >
                      #{{ sale.journal_entry_number || sale.journal_entry }}↗
                    </router-link>
                    <button
                      v-if="sale.status === 'ISSUED' && canWriteSales && periodStore.isPeriodOpen"
                      type="button"
                      class="ds-btn ds-btn--ghost ds-btn--sm"
                      style="padding: 2px 6px; font-size: 11px; color: #8c1d2c"
                      @click="promptVoidSale(sale)"
                    >
                      Anular
                    </button>
                    <span v-else-if="sale.status === 'VOIDED'" class="ds-badge badge-danger ds-badge--sm">ANULADA</span>
                  </div>
                </td>
              </tr>
            </tbody>

            <tfoot v-if="salesBook.totals">
              <tr>
                <td colspan="4">
                  <div class="flex-row gap-sm" style="align-items: center">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6b4c1b" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M18 6 7 17l-5-5" />
                      <path d="m22 10-7.5 7.5L13 16" />
                    </svg>
                    <span style="font-family: Georgia, serif; font-size: 16.5px; font-weight: 700; color: #1b1a19">
                      Totales del periodo
                    </span>
                    <span style="font-size: 11.5px; color: #7a736a; font-weight: 500">
                      (Sumas iguales comprobadas)
                    </span>
                  </div>
                </td>
                <td class="text-right mono" style="font-weight: 800; font-size: 14.5px; color: #1b1a19">
                  {{ formatRawNumber(salesBook.totals.taxable_amount) }}
                </td>
                <td class="text-right mono" style="font-weight: 800; font-size: 14.5px; color: #8c1d2c">
                  {{ formatRawNumber(salesBook.totals.iva_amount) }}
                </td>
                <td class="text-right mono" style="font-weight: 800; font-size: 15px; color: #6b1a24">
                  {{ formatRawNumber(salesBook.totals.total) }}
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </template>

      <!-- ==================== TAB 2: LIBRO LEGAL CONSUMIDOR FINAL (FCF) ==================== -->
      <template v-else-if="activeBookTab === 'fcf'">
        <div style="overflow-x: auto">
          <table class="ds-dark-table">
            <thead>
              <tr>
                <th>FECHA EMISIÓN</th>
                <th>DEL N.º (INICIAL)</th>
                <th>AL N.º (FINAL)</th>
                <th class="text-right">CANT. FCF</th>
                <th class="text-right">EXENTAS ($)</th>
                <th class="text-right">GRAVADAS LOCALES ($)</th>
                <th class="text-right">IVA DÉBITO 13% ($)</th>
                <th class="text-right">TOTAL DIARIO ($)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!salesBook.legal_fcf_book?.length">
                <td colspan="8" class="text-center text-muted" style="padding: 32px">
                  Sin facturas de consumidor final emitidas en el período.
                </td>
              </tr>
              <tr v-for="row in salesBook.legal_fcf_book" :key="row.sale_date">
                <td class="mono">{{ formatShortDate(row.sale_date) }}</td>
                <td><span class="ds-doc-pill">{{ row.from_doc }}</span></td>
                <td><span class="ds-doc-pill">{{ row.to_doc }}</span></td>
                <td class="text-right mono">{{ row.documents_count }}</td>
                <td class="text-right mono">0.00</td>
                <td class="text-right mono" style="font-weight: 600">{{ formatRawNumber(row.taxable_amount) }}</td>
                <td class="text-right mono" style="font-weight: 600; color: #8c1d2c">{{ formatRawNumber(row.iva_amount) }}</td>
                <td class="text-right mono" style="font-weight: 800">{{ formatRawNumber(row.total) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- ==================== TAB 3: LIBRO LEGAL CONTRIBUYENTES (CCF) ==================== -->
      <template v-else-if="activeBookTab === 'ccf'">
        <div style="overflow-x: auto">
          <table class="ds-dark-table">
            <thead>
              <tr>
                <th>FECHA</th>
                <th>TIPO</th>
                <th>CORRELATIVO</th>
                <th>CONTRIBUYENTE</th>
                <th>NRC</th>
                <th class="text-right">GRAVADO ($)</th>
                <th class="text-right">IVA 13% ($)</th>
                <th class="text-right">RET. 1% ($)</th>
                <th class="text-right">TOTAL ($)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!salesBook.legal_ccf_book?.length">
                <td colspan="9" class="text-center text-muted" style="padding: 32px">
                  No se han emitido Comprobantes de Crédito Fiscal (CCF) en este período.
                </td>
              </tr>
              <tr v-for="row in salesBook.legal_ccf_book" :key="row.id">
                <td class="mono">{{ formatShortDate(row.sale_date) }}</td>
                <td><span class="ds-regime-tag ds-regime-tag--cabina">{{ row.doc_type }}</span></td>
                <td><span class="ds-doc-pill">{{ row.doc_number }}</span></td>
                <td style="font-weight: 700">{{ row.customer_name }}</td>
                <td class="mono">{{ row.nrc }}</td>
                <td class="text-right mono">{{ formatRawNumber(row.taxable_amount) }}</td>
                <td class="text-right mono" style="color: #8c1d2c">{{ formatRawNumber(row.iva_amount) }}</td>
                <td class="text-right mono">{{ formatRawNumber(row.iva_withheld) }}</td>
                <td class="text-right mono" style="font-weight: 800">{{ formatRawNumber(row.total) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- Bottom Explanatory Audit Note Bar -->
      <div class="ds-audit-note-bar">
        <div class="ds-audit-note-bar__text">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            style="color: #7a736a; flex-shrink: 0; margin-top: 1px"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
          <span>
            Cada venta separa automáticamente la base gravada y el IVA débito fiscal del 13%. El motor contable distingue si corresponde a prestación de servicio (Cabina → Cuenta 510101) o venta de producto (Vitrina → Cuenta 510201) para dirigir el asiento a la cuenta de ingreso y control de inventario correcta.
          </span>
        </div>
        <div class="ds-audit-ok-tag">
          <span>AUDITORÍA OK</span>
          <span class="ds-status-pill__dot"></span>
        </div>
      </div>
    </div>

    <!-- Bottom 2 Regime Summary Cards: Cabina vs. Vitrina (RF-VEN-09) -->
    <div class="ds-bottom-regime-grid">
      <div class="ds-regime-summary-card" @click="selectMainFilter('all', 'SERVICE')">
        <div class="ds-regime-summary-card__left">
          <div class="ds-regime-summary-card__icon ds-regime-summary-card__icon--cabina">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 3c-2.5 3.5-4 7-4 10a4 4 0 0 0 8 0c0-3-1.5-6.5-4-10z" />
              <path d="M8 14c-3-1.5-5-1-6 1 2 2.5 5 3.5 8 3" />
              <path d="M16 14c3-1.5 5-1 6 1-2 2.5-5 3.5-8 3" />
            </svg>
          </div>
          <div>
            <div class="ds-regime-summary-card__eyebrow">SERVICIOS EN SALÓN (CABINA)</div>
            <div class="ds-regime-summary-card__amount-row">
              <span class="ds-regime-summary-card__amount">
                {{ formatMoney(salesBook.regime_summary?.cabina?.amount || '0.00') }}
              </span>
              <span class="ds-regime-summary-card__pct">
                ({{ salesBook.regime_summary?.cabina?.pct || '0.0%' }} del total)
              </span>
            </div>
            <div class="ds-regime-summary-card__sub">
              {{ salesBook.regime_summary?.cabina?.documents_count || 0 }} registros · Corte & peinado, Manicura
            </div>
          </div>
        </div>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#9b948b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </div>

      <div class="ds-regime-summary-card" @click="selectMainFilter('all', 'PRODUCT')">
        <div class="ds-regime-summary-card__left">
          <div class="ds-regime-summary-card__icon ds-regime-summary-card__icon--vitrina">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" />
              <line x1="3" y1="6" x2="21" y2="6" />
              <path d="M16 10a4 4 0 0 1-8 0" />
            </svg>
          </div>
          <div>
            <div class="ds-regime-summary-card__eyebrow">VENTA RETAIL DIRECTA (VITRINA)</div>
            <div class="ds-regime-summary-card__amount-row">
              <span class="ds-regime-summary-card__amount">
                {{ formatMoney(salesBook.regime_summary?.vitrina?.amount || '0.00') }}
              </span>
              <span class="ds-regime-summary-card__pct">
                ({{ salesBook.regime_summary?.vitrina?.pct || '0.0%' }} del total)
              </span>
            </div>
            <div class="ds-regime-summary-card__sub">
              {{ salesBook.regime_summary?.vitrina?.documents_count || 0 }} registros · Champú nutritivo, Sérum de brillo
            </div>
          </div>
        </div>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#9b948b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </div>
    </div>

    <!-- ==================== MODAL: + REGISTRAR VENTA (RF-VEN-01..05) ==================== -->
    <FormModal
      v-model="showSaleModal"
      title="Registrar Documento de Venta Fiscal"
      subtitle="Emisión correlativa FCF / CCF, desglose automático de IVA 13% y asiento contable en tiempo real."
      size="lg"
    >
      <div class="flex-col gap-md">
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px">
          <div>
            <label class="form-label">Tipo de Documento</label>
            <select v-model="saleForm.doc_type" class="form-select" @change="onDocTypeChange">
              <option value="FCF">Factura Consumidor Final (FCF)</option>
              <option value="CCF">Crédito Fiscal (CCF +13% IVA)</option>
              <option value="NC">Nota de Crédito (NC s/ CCF)</option>
            </select>
          </div>

          <div>
            <label class="form-label">Próximo Correlativo</label>
            <input :value="nextCorrelativePreview" type="text" class="form-input mono" disabled />
          </div>

          <div>
            <label class="form-label">Fecha de Emisión</label>
            <input v-model="saleForm.sale_date" type="date" class="form-input" />
          </div>

          <div>
            <label class="form-label">Método de Cobro</label>
            <select v-model="saleForm.payment_method" class="form-select">
              <option value="CASH">Efectivo (110101 Caja general)</option>
              <option value="CARD">Tarjeta POS (110103 Bancos)</option>
              <option value="TRANSFER">Transferencia (110103 Bancos)</option>
              <option value="CREDIT">Crédito Cliente (110201 Clientes)</option>
            </select>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px">
          <div>
            <label class="form-label">Cliente</label>
            <select v-model="saleForm.customer" class="form-select">
              <option v-for="c in filteredCustomersForDocType" :key="c.id" :value="c.id">
                {{ c.name }} {{ c.nrc ? `(NRC: ${c.nrc})` : '(Consumidor Final)' }} {{ c.is_large_taxpayer ? '· Gran Contrib.' : '' }}
              </option>
            </select>
          </div>

          <div v-if="saleForm.doc_type === 'NC'">
            <label class="form-label">CCF de Referencia</label>
            <select v-model="saleForm.related_sale" class="form-select">
              <option :value="null">Seleccione CCF origen...</option>
              <option v-for="ccf in availableCcfSales" :key="ccf.id" :value="ccf.id">
                {{ ccf.doc_number }} — {{ ccf.customer_name }} ({{ formatMoney(ccf.total) }})
              </option>
            </select>
          </div>

          <div>
            <label class="form-label">Observaciones / Estilista</label>
            <input
              v-model="saleForm.notes"
              type="text"
              class="form-input"
              placeholder="Ej. Atendido en Estación Cabina 1..."
            />
          </div>
        </div>

        <!-- Lines Editor -->
        <div class="card p-md" style="background: var(--bg-subtle)">
          <div class="flex-between mb-sm">
            <div class="eyebrow">LÍNEAS DE FACTURACIÓN (SERVICIOS CABINA & PRODUCTOS VITRINA)</div>
            <div class="flex-row gap-xs">
              <button type="button" class="btn btn--secondary btn--sm" @click="addSaleLine('SERVICE')">
                + Línea Servicio (Cabina)
              </button>
              <button type="button" class="btn btn--secondary btn--sm" @click="addSaleLine('PRODUCT')">
                + Línea Producto (Vitrina)
              </button>
            </div>
          </div>

          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 125px">Régimen</th>
                <th>Servicio / Producto Vitrina</th>
                <th style="width: 90px" class="text-right">Cant.</th>
                <th style="width: 120px" class="text-right">
                  {{ saleForm.doc_type === 'FCF' ? 'Precio c/IVA' : 'Valor Neto' }}
                </th>
                <th style="width: 120px" class="text-right">Subtotal</th>
                <th style="width: 45px"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(ln, idx) in saleForm.lines" :key="idx">
                <td>
                  <Badge :variant="ln.line_type === 'PRODUCT' ? 'accent' : 'neutral'">
                    {{ ln.line_type === 'PRODUCT' ? 'VITRINA' : 'CABINA' }}
                  </Badge>
                </td>
                <td>
                  <select
                    v-if="ln.line_type === 'SERVICE'"
                    v-model="ln.service_id"
                    class="form-select"
                    @change="onSelectLineService(ln)"
                  >
                    <option v-for="srv in services" :key="srv.id" :value="srv.id">
                      {{ srv.code }} · {{ srv.name }} (${{ srv.price }})
                    </option>
                  </select>
                  <select
                    v-else
                    v-model="ln.product_id"
                    class="form-select"
                    @change="onSelectLineProduct(ln)"
                  >
                    <option v-for="prd in vitrinaProducts" :key="prd.id" :value="prd.id">
                      {{ prd.sku }} · {{ prd.name }} (PVP ${{ prd.sale_price }} · Costo ${{ Number(prd.average_cost).toFixed(2) }})
                    </option>
                  </select>
                </td>
                <td>
                  <input
                    v-model.number="ln.quantity"
                    type="number"
                    min="1"
                    step="1"
                    class="form-input text-right mono"
                  />
                </td>
                <td>
                  <input
                    v-model.number="ln.unit_price"
                    type="number"
                    min="0.01"
                    step="0.01"
                    class="form-input text-right mono"
                  />
                </td>
                <td class="text-right mono" style="font-weight: 600">
                  {{ formatMoney((Number(ln.quantity || 0) * Number(ln.unit_price || 0)).toFixed(2)) }}
                </td>
                <td class="text-right">
                  <button
                    v-if="saleForm.lines.length > 1"
                    type="button"
                    class="btn btn--ghost btn--sm"
                    @click="saleForm.lines.splice(idx, 1)"
                  >
                    ✕
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Live Tax & Accounting Preview -->
        <div class="card p-md flex-between" style="flex-wrap: wrap; gap: 16px">
          <div>
            <div class="eyebrow">ASIENTO CONTABLE AUTOMÁTICO (RN-11)</div>
            <div class="text-muted" style="font-size: 12.5px; margin-top: 2px">
              Cargo a <strong>{{ paymentAccountLabel }}</strong> · Abono a <strong>510101/510201 Ingresos</strong> y <strong>210201 IVA Débito (13%)</strong>
              <span v-if="hasProductLines"> + Costo de Venta (<strong>410101 vs 110401</strong>)</span>
            </div>
          </div>

          <div class="flex-row gap-lg" style="align-items: center">
            <div class="text-right">
              <div class="text-muted" style="font-size: 11px">Base Gravada</div>
              <div class="mono" style="font-weight: 600">{{ formatMoney(livePreview.taxable) }}</div>
            </div>
            <div class="text-right">
              <div class="text-muted" style="font-size: 11px">IVA Débito (13%)</div>
              <div class="mono" style="font-weight: 600">{{ formatMoney(livePreview.iva) }}</div>
            </div>
            <div v-if="livePreview.withheld > 0" class="text-right">
              <div class="text-muted" style="font-size: 11px">Retención 1%</div>
              <div class="mono" style="font-weight: 600; color: var(--color-warning)">-{{ formatMoney(livePreview.withheld) }}</div>
            </div>
            <div class="text-right">
              <div class="text-muted" style="font-size: 11px">TOTAL DOCUMENTO</div>
              <div class="mono" style="font-size: 18px; font-weight: 700; color: var(--color-gold-deep)">
                {{ formatMoney(livePreview.total) }}
              </div>
            </div>
          </div>
        </div>

        <div v-if="formError" class="alert alert--danger">{{ formError }}</div>
      </div>

      <template #footer>
        <button type="button" class="btn btn--ghost" @click="showSaleModal = false">Cancelar</button>
        <button type="button" class="btn btn--primary" :disabled="submitting" @click="submitSale">
          {{ submitting ? 'Contabilizando...' : 'Emitir y Contabilizar Venta' }}
        </button>
      </template>
    </FormModal>

    <!-- ==================== MODAL: DETALLE DE VENTA ==================== -->
    <FormModal
      v-model="showDetailModal"
      :title="`Documento Fiscal ${selectedSale?.doc_type || ''} ${selectedSale?.doc_number || ''}`"
      :subtitle="`Cliente: ${selectedSale?.customer_name || ''} · Fecha: ${selectedSale?.sale_date || ''}`"
      size="md"
    >
      <div v-if="selectedSale" class="flex-col gap-md">
        <div class="flex-between card p-sm" style="background: var(--bg-subtle)">
          <span>Estado: <strong>{{ selectedSale.status_label }}</strong></span>
          <span>Método de Pago: <strong>{{ selectedSale.payment_method_label }}</strong></span>
          <router-link
            v-if="selectedSale.journal_entry"
            :to="{ path: '/diario', query: { entry: selectedSale.journal_entry } }"
            class="mono"
            style="color: var(--color-gold-deep); font-weight: 600"
          >
            Ver Partida #{{ selectedSale.journal_entry_number || selectedSale.journal_entry }} ↗
          </router-link>
        </div>

        <table class="data-table">
          <thead>
            <tr>
              <th>Régimen</th>
              <th>Descripción</th>
              <th class="text-right">Cant.</th>
              <th class="text-right">Gravado</th>
              <th class="text-right">IVA 13%</th>
              <th class="text-right">Total</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="ln in selectedSale.lines" :key="ln.id">
              <td><Badge :variant="ln.line_type === 'PRODUCT' ? 'accent' : 'neutral'">{{ ln.regime_badge }}</Badge></td>
              <td>{{ ln.description }}</td>
              <td class="text-right mono">{{ Number(ln.quantity).toFixed(0) }}</td>
              <td class="text-right mono">{{ formatMoney(ln.taxable_amount) }}</td>
              <td class="text-right mono">{{ formatMoney(ln.iva_amount) }}</td>
              <td class="text-right mono" style="font-weight: 600">{{ formatMoney(ln.total) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <template #footer>
        <button type="button" class="btn btn--primary" @click="showDetailModal = false">Cerrar</button>
      </template>
    </FormModal>

    <!-- ==================== MODAL: DIRECTORIO DE CLIENTES (RF-VEN-13) ==================== -->
    <FormModal
      v-model="showCustomersModal"
      title="Directorio de Clientes y Contribuyentes IVA"
      subtitle="Gestione clientes Consumidor Final y Contribuyentes con NRC para emisión de CCF."
      size="lg"
    >
      <div class="flex-col gap-md">
        <div class="card p-md" style="background: var(--bg-subtle)">
          <div class="eyebrow mb-xs">AGREGAR NUEVO CLIENTE</div>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px">
            <input v-model="newCustomer.name" type="text" class="form-input" placeholder="Nombre o Razón Social *" />
            <select v-model="newCustomer.customer_type" class="form-select">
              <option value="FINAL_CONSUMER">Consumidor Final</option>
              <option value="TAXPAYER">Contribuyente IVA (CCF)</option>
            </select>
            <input v-model="newCustomer.document_number" type="text" class="form-input" placeholder="NIT / DUI (0614-...)" />
            <input v-model="newCustomer.nrc" type="text" class="form-input" placeholder="NRC (ej. 284910-5)" />
          </div>
          <div class="flex-between mt-sm" style="margin-top: 10px">
            <label class="flex-row gap-xs" style="font-size: 12.5px; cursor: pointer">
              <input v-model="newCustomer.is_large_taxpayer" type="checkbox" />
              <span>Gran Contribuyente (aplica retención 1% IVA en CCF)</span>
            </label>
            <button type="button" class="btn btn--primary btn--sm" @click="createCustomerItem">
              + Guardar Cliente
            </button>
          </div>
          <div v-if="customerError" class="alert alert--danger mt-xs">{{ customerError }}</div>
        </div>

        <table class="data-table">
          <thead>
            <tr>
              <th>Nombre / Razón Social</th>
              <th>Tipo</th>
              <th>NIT / Documento</th>
              <th>NRC</th>
              <th>Gran Contribuyente</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in customers" :key="c.id">
              <td style="font-weight: 600">{{ c.name }}</td>
              <td><Badge :variant="c.customer_type === 'TAXPAYER' ? 'warning' : 'neutral'">{{ c.customer_type_label }}</Badge></td>
              <td class="mono">{{ c.document_number || '—' }}</td>
              <td class="mono">{{ c.nrc || '—' }}</td>
              <td>{{ c.is_large_taxpayer ? 'Sí (1%)' : 'No' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <template #footer>
        <button type="button" class="btn btn--ghost" @click="showCustomersModal = false">Cerrar</button>
      </template>
    </FormModal>

    <!-- ==================== MODAL: CATÁLOGO DE SERVICIOS (RF-VEN-13) ==================== -->
    <FormModal
      v-model="showServicesModal"
      title="Catálogo de Servicios de Belleza (Cabina · Subcuenta 510101..510103)"
      subtitle="Precios oficiales con IVA incluido (13%) para facturación rápida."
      size="lg"
    >
      <div class="flex-col gap-md">
        <div class="card p-md" style="background: var(--bg-subtle)">
          <div class="eyebrow mb-xs">NUEVO SERVICIO DE SALÓN</div>
          <div style="display: grid; grid-template-columns: 120px 1fr 160px 130px auto; gap: 10px; align-items: center">
            <input v-model="newService.code" type="text" class="form-input mono" placeholder="SRV-006" />
            <input v-model="newService.name" type="text" class="form-input" placeholder="Nombre del servicio..." />
            <select v-model="newService.category" class="form-select">
              <option value="STYLING">Peinado & Brushing</option>
              <option value="HAIRCUT">Corte</option>
              <option value="COLOR">Colorimetría</option>
              <option value="TREATMENT">Tratamiento</option>
              <option value="NAILS">Uñas & Spa</option>
            </select>
            <input v-model.number="newService.price" type="number" step="0.50" class="form-input text-right mono" placeholder="PVP $" />
            <button type="button" class="btn btn--primary btn--sm" @click="createServiceItem">
              + Agregar
            </button>
          </div>
        </div>

        <table class="data-table">
          <thead>
            <tr>
              <th>Código</th>
              <th>Servicio en Cabina</th>
              <th>Categoría</th>
              <th>Cuenta Ingreso</th>
              <th class="text-right">PVP (IVA Incl.)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in services" :key="s.id">
              <td class="mono" style="font-weight: 700">{{ s.code }}</td>
              <td style="font-weight: 600">{{ s.name }}</td>
              <td><Badge variant="neutral">{{ s.category_label }}</Badge></td>
              <td class="mono">{{ s.income_account_code || '510101' }}</td>
              <td class="text-right mono" style="font-weight: 700">{{ formatMoney(s.price) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <template #footer>
        <button type="button" class="btn btn--ghost" @click="showServicesModal = false">Cerrar</button>
      </template>
    </FormModal>

    <!-- ==================== DIALOG: ANULAR VENTA (RF-VEN-10) ==================== -->
    <ConfirmDialog
      v-model="showVoidDialog"
      :title="`Anular Documento ${saleToVoid?.doc_number || ''}`"
      message="Esta acción generará automáticamente la partida de reversión en el Libro Diario y dejará constancia en la bitácora de auditoría."
      confirm-text="Confirmar Anulación"
      variant="danger"
      require-reason
      reason-label="Motivo de anulación fiscal (obligatorio)"
      @confirm="executeVoidSale"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import http from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { usePeriodStore } from '@/stores/period'
import { formatMoney } from '@/utils/formatters'
import {
  Badge,
  ConfirmDialog,
  DateRangePicker,
  ExportButton,
  FormModal,
  KpiCard,
  MoneyCell,
  SearchInput,
} from '@/components/ui'

const route = useRoute()
const authStore = useAuthStore()
const periodStore = usePeriodStore()

const activeBookTab = ref('all')
const filterLineType = ref('')
const filterDocType = ref('')
const searchQuery = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const showRangeInputs = ref(false)

function formatShortDate(isoStr) {
  if (!isoStr || typeof isoStr !== 'string') return '—'
  const parts = isoStr.slice(0, 10).split('-')
  if (parts.length !== 3) return isoStr
  return `${parts[2]}/${parts[1]}/${parts[0].slice(2)}`
}

function formatRawNumber(val) {
  const num = Number(val || 0)
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function isFinalConsumerName(name) {
  if (!name) return true
  return name.toLowerCase().includes('consumidor final')
}

const periodShortRangeLabel = computed(() => {
  const start = periodStore.activePeriod?.start_date
  const end = periodStore.activePeriod?.end_date
  if (start && end) {
    const s = start.split('-')
    const e = end.split('-')
    return `${s[2]}/${s[1]} – ${e[2]}/${e[1]}`
  }
  return '01/11 – 30/11'
})

const formattedRangeDisplay = computed(() => {
  if (dateFrom.value && dateTo.value) {
    return `${formatShortDate(dateFrom.value)} - ${formatShortDate(dateTo.value)}`
  }
  const salesList = salesBook.value.sales || []
  if (salesList.length > 0) {
    const dates = salesList.map((s) => s.sale_date).sort()
    const first = dates[0]?.slice(0, 8) + '01'
    const last = dates[dates.length - 1]
    return `${formatShortDate(first)} - ${formatShortDate(last)}`
  }
  const start = periodStore.activePeriod?.start_date
  const end = periodStore.activePeriod?.end_date
  if (start && end) {
    return `${formatShortDate(start)} - ${formatShortDate(end)}`
  }
  return '01/11/26 - 30/11/26'
})

function selectMainFilter(tab, lineType = '') {
  activeBookTab.value = tab
  filterLineType.value = lineType
  fetchSalesBook()
}

function clearDateFilter() {
  dateFrom.value = ''
  dateTo.value = ''
  filterDocType.value = ''
  fetchSalesBook()
}

function printSalesBook() {
  window.print()
}

const salesBook = ref({
  kpis: {},
  regime_summary: {},
  counts: {},
  sales: [],
  legal_fcf_book: [],
  legal_ccf_book: [],
  totals: {},
})

const customers = ref([])
const services = ref([])
const documentSeries = ref([])
const vitrinaProducts = ref([])

const showSaleModal = ref(false)
const showDetailModal = ref(false)
const showCustomersModal = ref(false)
const showServicesModal = ref(false)
const showVoidDialog = ref(false)

const selectedSale = ref(null)
const saleToVoid = ref(null)
const submitting = ref(false)
const formError = ref('')
const customerError = ref('')

const saleForm = ref({
  doc_type: 'FCF',
  sale_date: '2026-11-08',
  customer: null,
  payment_method: 'CASH',
  related_sale: null,
  notes: '',
  lines: [],
})

const newCustomer = ref({
  name: '',
  customer_type: 'TAXPAYER',
  document_type: 'NIT',
  document_number: '',
  nrc: '',
  is_large_taxpayer: false,
})

const newService = ref({
  code: '',
  name: '',
  category: 'STYLING',
  price: 25.0,
})

const canWriteSales = computed(() => {
  const role = authStore.user?.role
  return ['ADMIN', 'ACCOUNTANT', 'CASHIER'].includes(role)
})

const exportBookKey = computed(() => {
  if (activeBookTab.value === 'fcf') return 'sales-fcf'
  if (activeBookTab.value === 'ccf') return 'sales-ccf'
  return 'sales'
})

const exportParams = computed(() => {
  const params = {}
  if (periodStore.activePeriod?.id) params.period = periodStore.activePeriod.id
  return params
})

const nextCorrelativePreview = computed(() => {
  const s = documentSeries.value.find((item) => item.doc_type === saleForm.value.doc_type && item.is_active)
  return s ? s.next_formatted : `${saleForm.value.doc_type}-0001`
})

const filteredCustomersForDocType = computed(() => {
  if (saleForm.value.doc_type === 'FCF') return customers.value
  return customers.value.filter((c) => c.customer_type === 'TAXPAYER')
})

const availableCcfSales = computed(() =>
  (salesBook.value.sales || []).filter((s) => s.doc_type === 'CCF' && s.status === 'ISSUED')
)

const paymentAccountLabel = computed(() => {
  const m = saleForm.value.payment_method
  if (m === 'CASH') return '110101 Caja general'
  if (m === 'CARD' || m === 'TRANSFER') return '110103 Bancos cuenta corriente'
  return '110201 Clientes (CxC)'
})

const hasProductLines = computed(() =>
  saleForm.value.lines.some((l) => l.line_type === 'PRODUCT')
)

const livePreview = computed(() => {
  const isFcf = saleForm.value.doc_type === 'FCF'
  let taxable = 0
  let iva = 0
  for (const ln of saleForm.value.lines) {
    const gross = Number(ln.quantity || 0) * Number(ln.unit_price || 0)
    if (gross <= 0) continue
    if (isFcf) {
      const t = Math.round((gross / 1.13) * 100) / 100
      const v = Math.round((gross - t) * 100) / 100
      taxable += t
      iva += v
    } else {
      const t = Math.round(gross * 100) / 100
      const v = Math.round(t * 0.13 * 100) / 100
      taxable += t
      iva += v
    }
  }
  const cust = customers.value.find((c) => c.id === saleForm.value.customer)
  const withheld =
    !isFcf && cust?.is_large_taxpayer ? Math.round(taxable * 0.01 * 100) / 100 : 0
  const total = Math.round((taxable + iva - withheld) * 100) / 100
  return {
    taxable: taxable.toFixed(2),
    iva: iva.toFixed(2),
    withheld: withheld.toFixed(2),
    total: total.toFixed(2),
  }
})

async function fetchCatalogs() {
  const [custRes, srvRes, serRes] = await Promise.all([
    http.get('/v1/customers/'),
    http.get('/v1/services/'),
    http.get('/v1/document-series/'),
  ])
  customers.value = Array.isArray(custRes.data) ? custRes.data : custRes.data.results || []
  services.value = Array.isArray(srvRes.data) ? srvRes.data : srvRes.data.results || []
  documentSeries.value = Array.isArray(serRes.data) ? serRes.data : serRes.data.results || []
}

async function fetchSalesBook() {
  const params = {}
  if (periodStore.activePeriod?.id) params.period = periodStore.activePeriod.id
  if (filterDocType.value) params.doc_type = filterDocType.value
  if (filterLineType.value) params.line_type = filterLineType.value
  if (searchQuery.value) params.search = searchQuery.value
  if (dateFrom.value) params.date_from = dateFrom.value
  if (dateTo.value) params.date_to = dateTo.value

  const { data } = await http.get('/v1/sales-book/', { params })
  salesBook.value = data
  if (data.vitrina_products) {
    vitrinaProducts.value = data.vitrina_products
  }
}

function setLineFilter(type) {
  filterLineType.value = type
  fetchSalesBook()
}

function openNewSaleModal() {
  formError.value = ''
  const defaultCust = customers.value.find((c) => c.is_generic) || customers.value[0]
  const defaultSrv = services.value[0]
  saleForm.value = {
    doc_type: 'FCF',
    sale_date: periodStore.activePeriod?.end_date || '2026-11-08',
    customer: defaultCust?.id || null,
    payment_method: 'CASH',
    related_sale: null,
    notes: '',
    lines: [
      {
        line_type: 'SERVICE',
        service_id: defaultSrv?.id || null,
        product_id: null,
        quantity: 1,
        unit_price: Number(defaultSrv?.price || 25.0),
      },
    ],
  }
  showSaleModal.value = true
}

function onDocTypeChange() {
  if (saleForm.value.doc_type !== 'FCF') {
    const tp = customers.value.find((c) => c.customer_type === 'TAXPAYER')
    if (tp) saleForm.value.customer = tp.id
  } else {
    const cf = customers.value.find((c) => c.is_generic)
    if (cf) saleForm.value.customer = cf.id
  }
}

function addSaleLine(type) {
  if (type === 'SERVICE') {
    const srv = services.value[0]
    saleForm.value.lines.push({
      line_type: 'SERVICE',
      service_id: srv?.id || null,
      product_id: null,
      quantity: 1,
      unit_price: Number(srv?.price || 25.0),
    })
  } else {
    const prd = vitrinaProducts.value[0]
    saleForm.value.lines.push({
      line_type: 'PRODUCT',
      service_id: null,
      product_id: prd?.id || 1,
      quantity: 1,
      unit_price: Number(prd?.sale_price || 12.0),
    })
  }
}

function onSelectLineService(ln) {
  const srv = services.value.find((s) => s.id === ln.service_id)
  if (srv) ln.unit_price = Number(srv.price)
}

function onSelectLineProduct(ln) {
  const prd = vitrinaProducts.value.find((p) => p.id === ln.product_id)
  if (prd) ln.unit_price = Number(prd.sale_price)
}

async function submitSale() {
  submitting.value = true
  formError.value = ''
  try {
    await http.post('/v1/sales/', saleForm.value)
    showSaleModal.value = false
    await Promise.all([fetchSalesBook(), fetchCatalogs()])
  } catch (err) {
    formError.value = err.response?.data?.detail || 'No se pudo registrar la venta.'
  } finally {
    submitting.value = false
  }
}

function inspectSale(sale) {
  selectedSale.value = sale
  showDetailModal.value = true
}

function promptVoidSale(sale) {
  saleToVoid.value = sale
  showVoidDialog.value = true
}

async function executeVoidSale(reason) {
  if (!saleToVoid.value) return
  await http.post(`/v1/sales/${saleToVoid.value.id}/void/`, { reason })
  showVoidDialog.value = false
  await fetchSalesBook()
}

async function createCustomerItem() {
  customerError.value = ''
  try {
    await http.post('/v1/customers/', newCustomer.value)
    newCustomer.value = {
      name: '',
      customer_type: 'TAXPAYER',
      document_type: 'NIT',
      document_number: '',
      nrc: '',
      is_large_taxpayer: false,
    }
    await fetchCatalogs()
  } catch (err) {
    customerError.value =
      err.response?.data?.non_field_errors?.[0] ||
      err.response?.data?.detail ||
      'Verifique los datos del cliente (NIT y NRC requeridos para contribuyentes).'
  }
}

async function createServiceItem() {
  if (!newService.value.code || !newService.value.name) return
  await http.post('/v1/services/', newService.value)
  newService.value = { code: '', name: '', category: 'STYLING', price: 25.0 }
  await fetchCatalogs()
}

watch(
  () => periodStore.activePeriod?.id,
  () => {
    dateFrom.value = ''
    dateTo.value = ''
    fetchSalesBook()
  }
)

onMounted(async () => {
  if (route.query.doc) {
    searchQuery.value = String(route.query.doc)
  }
  await Promise.all([fetchCatalogs(), fetchSalesBook()])
})
</script>
