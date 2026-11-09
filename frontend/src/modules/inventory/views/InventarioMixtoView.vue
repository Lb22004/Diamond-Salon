<template>
  <div class="ds-page">
    <!-- Top Responsibility Ribbon (Mock-up Exact) -->
    <div class="ds-vista-ribbon ds-vista-ribbon--soft">
      <div class="ds-vista-ribbon__left">
        <span class="ds-vista-ribbon__dot"></span>
        <span>VISTA 2 · INVENTARIO MIXTO: VENTA VS. SERVICIO</span>
      </div>
      <div class="ds-vista-ribbon__right">
        <span style="text-transform: none; font-weight: 600; color: #6e5c3e">Responsable:</span>
        <span class="ds-vista-ribbon__pill-pink">FERDINAND</span>
      </div>
    </div>

    <!-- Header Row -->
    <div class="ds-page-header" style="align-items: flex-start; margin-top: 0.25rem">
      <div>
        <h1 class="ds-serif-title" style="display: flex; align-items: center; gap: 0.65rem">
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--wine)"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" />
            <path d="m3.3 7 8.7 5 8.7-5" />
            <path d="M12 22V12" />
          </svg>
          <span>Inventario Mixto</span>
        </h1>
        <p class="ds-serif-subtitle">
          Separado rigurosamente en dos regímenes contables para evitar la distorsión de costos
          operativos y márgenes comerciales en el atelier.
        </p>
      </div>

      <div class="ds-header-actions-row">
        <button type="button" class="ds-btn ds-btn--outline" @click="openConsumptionModal">
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
            <circle cx="6" cy="6" r="3" />
            <path d="M8.12 8.12 12 12" />
            <path d="M20 4 8.12 15.88" />
            <circle cx="6" cy="18" r="3" />
            <path d="M14.8 14.8 20 20" />
          </svg>
          <span>Consumo cabina</span>
        </button>

        <button type="button" class="ds-btn ds-btn--outline" @click="openTransferModal">
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
            <path d="m16 3 4 4-4 4" />
            <path d="M20 7H4" />
            <path d="m8 21-4-4 4-4" />
            <path d="M4 17h16" />
          </svg>
          <span>Transferir</span>
        </button>

        <button type="button" class="ds-btn ds-btn--outline" @click="openAdjustmentModal">
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
            <line x1="4" y1="21" x2="4" y2="14" />
            <line x1="4" y1="10" x2="4" y2="3" />
            <line x1="12" y1="21" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12" y2="3" />
            <line x1="20" y1="21" x2="20" y2="16" />
            <line x1="20" y1="12" x2="20" y2="3" />
            <line x1="1" y1="14" x2="7" y2="14" />
            <line x1="9" y1="8" x2="15" y2="8" />
            <line x1="17" y1="16" x2="23" y2="16" />
          </svg>
          <span>Ajuste de stock</span>
        </button>

        <button type="button" class="ds-btn ds-btn--primary" @click="openProductModal">
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
          <span>+ Agregar producto</span>
        </button>
      </div>
    </div>

    <div v-if="feedbackMsg" class="ds-alert ds-alert--success">
      {{ feedbackMsg }}
    </div>
    <div v-if="errorMsg" class="ds-alert ds-alert--danger">
      {{ errorMsg }}
    </div>

    <!-- 3 KPI Cards Row (Mock-up Exact) -->
    <div class="ds-inv-kpi-grid">
      <!-- Card 1: Stock Vitrina (Retail) -->
      <div class="ds-inv-kpi-card ds-inv-kpi-card--wine">
        <div class="ds-inv-kpi-card__top">
          <div>
            <div class="ds-inv-kpi-card__eyebrow">STOCK VITRINA (RETAIL)</div>
            <div class="ds-inv-kpi-card__value ds-inv-kpi-card__value--wine">
              {{ summary.kpis.vitrina.units_total }} items
            </div>
          </div>
          <span class="ds-inv-kpi-card__icon ds-inv-kpi-card__icon--wine" aria-hidden="true">
            <svg
              width="20"
              height="20"
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
        <div class="ds-inv-kpi-footbox ds-inv-kpi-footbox--wine">
          <span>Valoración total</span>
          <strong>${{ summary.kpis.vitrina.cost_valuation }} Costo · ${{ summary.kpis.vitrina.pvp_valuation }} PVP</strong>
        </div>
      </div>

      <!-- Card 2: Insumos Cabina (Servicio) -->
      <div class="ds-inv-kpi-card ds-inv-kpi-card--ink">
        <div class="ds-inv-kpi-card__top">
          <div>
            <div class="ds-inv-kpi-card__eyebrow">INSUMOS CABINA (SERVICIO)</div>
            <div class="ds-inv-kpi-card__value">
              {{ summary.kpis.cabina.units_total }} items
            </div>
          </div>
          <span class="ds-inv-kpi-card__icon ds-inv-kpi-card__icon--ink" aria-hidden="true">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M12 3c-1.5 3.5-4.5 6-8 7 3.5 1 6.5 3.5 8 7 1.5-3.5 4.5-6 8-7-3.5-1-6.5-3.5-8-7Z" />
              <path d="M5 19c2-1 4-1 7-1s5 0 7 1" />
            </svg>
          </span>
        </div>
        <div class="ds-inv-kpi-footbox ds-inv-kpi-footbox--gold">
          <span>Costo activo amortizable</span>
          <strong>${{ summary.kpis.cabina.cost_valuation }} Costo</strong>
        </div>
      </div>

      <!-- Card 3: Alerta Stock Crítico -->
      <div class="ds-inv-kpi-card ds-inv-kpi-card--alert">
        <div class="ds-inv-kpi-card__top">
          <div>
            <div class="ds-inv-kpi-card__eyebrow">ALERTA STOCK CRÍTICO</div>
            <div class="ds-inv-kpi-card__value ds-inv-kpi-card__value--danger">
              {{ summary.kpis.critical.count }} items
            </div>
          </div>
          <span class="ds-inv-kpi-card__icon ds-inv-kpi-card__icon--danger" aria-hidden="true">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <line x1="12" y1="8" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </span>
        </div>
        <div class="ds-inv-kpi-footbox ds-inv-kpi-footbox--alert">
          <span>Reabastecimiento sugerido</span>
          <strong>{{ summary.kpis.critical.suggested_restock }}</strong>
        </div>
      </div>
    </div>

    <!-- Dual Side-by-Side Regime Panels (Vitrina vs Cabina) -->
    <div class="ds-inv-dual-grid">
      <!-- LEFT PANEL: Vitrina · para la venta (Wine Header) -->
      <section class="ds-inv-panel">
        <div>
          <div class="ds-inv-panel__header ds-inv-panel__header--wine">
            <div class="ds-inv-panel__title-group">
              <svg
                width="20"
                height="20"
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
              <div>
                <h2 class="ds-inv-panel__title">Vitrina · para la venta</h2>
                <p class="ds-inv-panel__subtitle">Generación de ingreso comercial directo</p>
              </div>
            </div>
            <span class="ds-inv-panel__count-pill">
              {{ summary.kpis.vitrina.units_total }} items
            </span>
          </div>

          <!-- Search & Account Tag -->
          <div class="ds-inv-panel__searchbar">
            <div class="ds-inv-panel__search-input">
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
                v-model="searchVitrina"
                type="text"
                placeholder="Filtrar vitrina..."
                @input="fetchSummary"
              />
            </div>
            <span class="ds-inv-panel__account-tag">CUENTA CONTABLE: 1104-01</span>
          </div>

          <!-- Vitrina Table -->
          <table class="ds-inv-table">
            <thead>
              <tr>
                <th>DESCRIPCIÓN DE PRODUCTO</th>
                <th class="text-right">EXISTENCIA</th>
                <th class="text-right">PVP UNITARIO</th>
                <th class="text-right">CLASIFICACIÓN</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!summary.vitrina_items.length">
                <td colspan="4" class="ds-table__state">
                  No se encontraron productos de vitrina con ese filtro.
                </td>
              </tr>
              <tr
                v-for="item in summary.vitrina_items"
                :key="item.id"
                title="Clic para inspeccionar Kárdex de costo promedio"
                @click="openKardexModal(item)"
              >
                <td>
                  <div class="ds-inv-prod-name">
                    <span>{{ item.name }}</span>
                    <span
                      v-if="item.is_critical"
                      class="ds-inv-crit-dot"
                      title="Stock crítico"
                    ></span>
                  </div>
                  <div class="ds-inv-prod-brand">{{ item.brand }}</div>
                </td>
                <td class="text-right">
                  <span
                    class="ds-inv-qty"
                    :class="{ 'ds-inv-qty--critical': item.is_critical }"
                  >
                    {{ item.quantity_display }}
                  </span>
                </td>
                <td class="text-right">
                  <span class="ds-inv-pvp">${{ item.sale_price }}</span>
                </td>
                <td class="text-right">
                  <span class="ds-inv-badge-venta">Venta</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Vitrina Footer -->
        <div class="ds-inv-panel__footer">
          <div class="ds-inv-panel__footer-label">
            SUBTOTAL INVENTARIO<br />VITRINA
          </div>
          <div class="ds-inv-panel__footer-units">
            {{ summary.kpis.vitrina.units_total }} unidades<br />físicas
          </div>
          <div class="ds-inv-panel__footer-box ds-inv-panel__footer-box--wine">
            ${{ summary.kpis.vitrina.cost_valuation }}<br />Valuado
          </div>
        </div>
      </section>

      <!-- RIGHT PANEL: Cabina · insumos de servicio (Dark Ink Header) -->
      <section class="ds-inv-panel">
        <div>
          <div class="ds-inv-panel__header ds-inv-panel__header--ink">
            <div class="ds-inv-panel__title-group">
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#e6c587"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <circle cx="6" cy="6" r="3" />
                <path d="M8.12 8.12 12 12" />
                <path d="M20 4 8.12 15.88" />
                <circle cx="6" cy="18" r="3" />
                <path d="M14.8 14.8 20 20" />
              </svg>
              <div>
                <h2 class="ds-inv-panel__title">Cabina · insumos de servicio</h2>
                <p class="ds-inv-panel__subtitle">Material de uso técnico interno en atelier</p>
              </div>
            </div>
            <span class="ds-inv-panel__count-pill">
              {{ summary.kpis.cabina.units_total }} items
            </span>
          </div>

          <!-- Search & Account Tag -->
          <div class="ds-inv-panel__searchbar">
            <div class="ds-inv-panel__search-input">
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
                v-model="searchCabina"
                type="text"
                placeholder="Filtrar insumos..."
                @input="fetchSummary"
              />
            </div>
            <span class="ds-inv-panel__account-tag">CUENTA CONTABLE: 1104-02</span>
          </div>

          <!-- Cabina Table -->
          <table class="ds-inv-table">
            <thead>
              <tr>
                <th>INSUMO TÉCNICO</th>
                <th class="text-right">EXISTENCIA</th>
                <th class="text-center">UBICACIÓN / ESTACIÓN</th>
                <th class="text-right">CLASIFICACIÓN</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!summary.cabina_items.length">
                <td colspan="4" class="ds-table__state">
                  No se encontraron insumos técnicos con ese filtro.
                </td>
              </tr>
              <tr
                v-for="item in summary.cabina_items"
                :key="item.id"
                title="Clic para inspeccionar Kárdex de costo promedio"
                @click="openKardexModal(item)"
              >
                <td>
                  <div class="ds-inv-prod-name">
                    <span>{{ item.name }}</span>
                    <span
                      v-if="item.is_critical"
                      class="ds-inv-crit-dot"
                      title="Stock crítico"
                    ></span>
                  </div>
                  <div class="ds-inv-prod-brand">{{ item.brand }}</div>
                </td>
                <td class="text-right">
                  <span
                    class="ds-inv-qty"
                    :class="{ 'ds-inv-qty--critical': item.is_critical }"
                  >
                    {{ item.quantity_display }}
                  </span>
                </td>
                <td class="text-center">
                  <span class="ds-inv-station-pill">{{ item.location_name }}</span>
                </td>
                <td class="text-right">
                  <span class="ds-inv-badge-servicio">Servicio</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Cabina Footer -->
        <div class="ds-inv-panel__footer">
          <div class="ds-inv-panel__footer-label">
            CONSUMO<br />ASIGNADO
          </div>
          <div class="ds-inv-panel__footer-units">
            {{ summary.kpis.cabina.units_total }}<br />unidades/litros
          </div>
          <div class="ds-inv-panel__footer-box">
            {{ summary.kpis.cabina.active_stations }} Estaciones<br />Activas
          </div>
        </div>
      </section>
    </div>

    <!-- Bottom Explanatory Rule Bar (Mock-up Exact) -->
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
          style="flex-shrink: 0; margin-top: 2px"
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4" />
          <path d="M12 8h.01" />
        </svg>
        <span>
          <strong style="font-style: normal; color: var(--ink)">Regla de Contabilización:</strong>
          Dos columnas claras: en rojo/vino lo que está a la venta (vitrina) y en negro/dorado lo
          que se usa en los servicios (cabina). Así se evita mezclar costos y márgenes en los
          asientos de cierre contable periódicos.
        </span>
      </div>
      <div class="ds-header-actions-row">
        <ExportButton book="inventory" label="Exportar inventario" />
      </div>
    </div>

    <!-- MODAL 1: + Agregar Producto (RF-INV-04) -->
    <ModalDialog
      v-model="showProductModal"
      title="Registrar nuevo artículo en Inventario Mixto"
      subtitle="Asigna automáticamente la cuenta contable según el régimen: Vitrina (110401) o Cabina (110402)."
      size="md"
    >
      <form class="flex-col gap-md" @submit.prevent="submitNewProduct">
        <div class="ds-form-grid">
          <div class="ds-field">
            <label class="ds-field__label">Régimen Contable (RN-07) *</label>
            <select v-model="productForm.inventory_type" class="ds-input" required>
              <option value="VITRINA">Vitrina · Para la venta (Cuenta 110401)</option>
              <option value="CABINA">Cabina · Insumo de servicio (Cuenta 110402)</option>
            </select>
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Código SKU *</label>
            <input v-model="productForm.sku" type="text" class="ds-input" placeholder="Ej. VIT-005" required />
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Nombre de Producto / Insumo *</label>
            <input
              v-model="productForm.name"
              type="text"
              class="ds-input"
              placeholder="Ej. Acondicionador Keratina 300ml"
              required
            />
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Marca / Línea Técnica</label>
            <input
              v-model="productForm.brand"
              type="text"
              class="ds-input"
              placeholder="Ej. L'Oréal Professionnel"
            />
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Unidad de Medida *</label>
            <select v-model="productForm.unit_of_measure" class="ds-input">
              <option value="UNIT">Unidad (u)</option>
              <option value="LITER">Litro (L)</option>
              <option value="MILLILITER">Mililitro (ml)</option>
              <option value="PACKAGE">Paquete (paq)</option>
            </select>
          </div>
          <div v-if="productForm.inventory_type === 'VITRINA'" class="ds-field">
            <label class="ds-field__label">PVP Unitario ($ con IVA) *</label>
            <input
              v-model="productForm.sale_price"
              type="number"
              step="0.01"
              min="0.01"
              class="ds-input"
              required
            />
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Costo Promedio Inicial ($)</label>
            <input
              v-model="productForm.average_cost"
              type="number"
              step="0.01"
              min="0"
              class="ds-input"
            />
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Stock Mínimo (Alerta Crítica)</label>
            <input
              v-model="productForm.min_stock"
              type="number"
              step="1"
              min="0"
              class="ds-input"
            />
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Existencia Inicial</label>
            <input
              v-model="productForm.initial_quantity"
              type="number"
              step="1"
              min="0"
              class="ds-input"
            />
          </div>
        </div>
        <div class="ds-modal__footer" style="padding: 0.75rem 0 0; background: transparent">
          <button type="button" class="ds-btn ds-btn--outline" @click="showProductModal = false">
            Cancelar
          </button>
          <button type="submit" class="ds-btn ds-btn--primary" :disabled="submitting">
            {{ submitting ? 'Guardando...' : 'Guardar artículo' }}
          </button>
        </div>
      </form>
    </ModalDialog>

    <!-- MODAL 2: Ajuste de Stock (RF-INV-08) -->
    <ModalDialog
      v-model="showAdjustmentModal"
      title="Ajuste de Stock Físico (Merma / Sobrante)"
      subtitle="Genera automáticamente la partida contable contra Faltantes (420102) o Sobrantes (5201)."
      size="md"
    >
      <form class="flex-col gap-md" @submit.prevent="submitAdjustment">
        <div class="ds-form-grid">
          <div class="ds-field">
            <label class="ds-field__label">Fecha del Ajuste *</label>
            <input v-model="adjustmentForm.adjustment_date" type="date" class="ds-input" required />
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Motivo de Auditoría *</label>
            <select v-model="adjustmentForm.reason" class="ds-input" required>
              <option value="PHYSICAL_COUNT">Conteo físico cíclico</option>
              <option value="DAMAGE">Deterioro o rotura en salón</option>
              <option value="EXPIRED">Vencimiento de lote</option>
              <option value="THEFT">Extravío / Merma</option>
              <option value="OTHER">Otro ajuste autorizado</option>
            </select>
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Artículo *</label>
            <select v-model="adjustmentForm.product_id" class="ds-input" required>
              <option v-for="p in allProducts" :key="p.id" :value="p.id">
                [{{ p.inventory_type }}] {{ p.sku }} · {{ p.name }} (Actual: {{ p.quantity_display }})
              </option>
            </select>
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Tipo de Ajuste *</label>
            <select v-model="adjustmentForm.direction" class="ds-input" required>
              <option value="OUT">Salida por Faltante / Merma (Cargo a 420102)</option>
              <option value="IN">Entrada por Sobrante (Abono a 5201)</option>
            </select>
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Cantidad a Ajustar *</label>
            <input
              v-model="adjustmentForm.quantity"
              type="number"
              step="0.01"
              min="0.01"
              class="ds-input"
              required
            />
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Justificación / Acta</label>
            <input
              v-model="adjustmentForm.notes"
              type="text"
              class="ds-input"
              placeholder="Ej. Envase dañado durante exhibición"
            />
          </div>
        </div>
        <div class="ds-modal__footer" style="padding: 0.75rem 0 0; background: transparent">
          <button type="button" class="ds-btn ds-btn--outline" @click="showAdjustmentModal = false">
            Cancelar
          </button>
          <button type="submit" class="ds-btn ds-btn--primary" :disabled="submitting">
            {{ submitting ? 'Contabilizando...' : 'Aplicar ajuste y contabilizar' }}
          </button>
        </div>
      </form>
    </ModalDialog>

    <!-- MODAL 3: Consumo de Insumos en Cabina (RF-INV-09) -->
    <ModalDialog
      v-model="showConsumptionModal"
      title="Registrar Consumo Técnico en Cabina"
      subtitle="Descarga existencias de estación y contabiliza Debe 410201 Costo de insumos / Haber 110402 Cabina."
      size="md"
    >
      <form class="flex-col gap-md" @submit.prevent="submitConsumption">
        <div class="ds-form-grid">
          <div class="ds-field">
            <label class="ds-field__label">Fecha de Consumo *</label>
            <input v-model="consumptionForm.consumption_date" type="date" class="ds-input" required />
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Estación de Cabina *</label>
            <select v-model="consumptionForm.location" class="ds-input" required>
              <option
                v-for="loc in cabinaLocations"
                :key="loc.code"
                :value="loc.code"
              >
                {{ loc.name }} ({{ loc.code }})
              </option>
            </select>
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Insumo Técnico (Solo Cabina) *</label>
            <select v-model="consumptionForm.product_id" class="ds-input" required>
              <option v-for="p in summary.cabina_items" :key="p.id" :value="p.id">
                {{ p.sku }} · {{ p.name }} (Disp: {{ p.quantity_display }} en {{ p.location_name }})
              </option>
            </select>
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Cantidad Consumida *</label>
            <input
              v-model="consumptionForm.quantity"
              type="number"
              step="0.01"
              min="0.01"
              class="ds-input"
              required
            />
          </div>
        </div>
        <div class="ds-field">
          <label class="ds-field__label">Servicio / Observaciones de Estación</label>
          <input
            v-model="consumptionForm.notes"
            type="text"
            class="ds-input"
            placeholder="Ej. Aplicación de tinte y sellador en cliente de Cabina 1"
          />
        </div>
        <div class="ds-modal__footer" style="padding: 0.75rem 0 0; background: transparent">
          <button type="button" class="ds-btn ds-btn--outline" @click="showConsumptionModal = false">
            Cancelar
          </button>
          <button type="submit" class="ds-btn ds-btn--primary" :disabled="submitting">
            {{ submitting ? 'Registrando...' : 'Registrar consumo' }}
          </button>
        </div>
      </form>
    </ModalDialog>

    <!-- MODAL 4: Transferencia entre Estaciones (RF-INV-12) -->
    <ModalDialog
      v-model="showTransferModal"
      title="Transferencia de Existencias entre Estaciones"
      subtitle="Traslada insumos entre Bodega General y Cabinas con trazabilidad completa en Kárdex."
      size="md"
    >
      <form class="flex-col gap-md" @submit.prevent="submitTransfer">
        <div class="ds-form-grid">
          <div class="ds-field">
            <label class="ds-field__label">Fecha de Transferencia *</label>
            <input v-model="transferForm.transfer_date" type="date" class="ds-input" required />
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Insumo a Trasladar *</label>
            <select v-model="transferForm.product_id" class="ds-input" required>
              <option v-for="p in summary.cabina_items" :key="p.id" :value="p.id">
                {{ p.sku }} · {{ p.name }} (Actual: {{ p.quantity_display }} en {{ p.location_name }})
              </option>
            </select>
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Ubicación Origen *</label>
            <select v-model="transferForm.from_location" class="ds-input" required>
              <option v-for="loc in cabinaLocations" :key="loc.code" :value="loc.code">
                {{ loc.name }} ({{ loc.code }})
              </option>
            </select>
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Ubicación Destino *</label>
            <select v-model="transferForm.to_location" class="ds-input" required>
              <option v-for="loc in cabinaLocations" :key="loc.code" :value="loc.code">
                {{ loc.name }} ({{ loc.code }})
              </option>
            </select>
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Cantidad a Transferir *</label>
            <input
              v-model="transferForm.quantity"
              type="number"
              step="0.01"
              min="0.01"
              class="ds-input"
              required
            />
          </div>
          <div class="ds-field">
            <label class="ds-field__label">Notas de Traslado</label>
            <input
              v-model="transferForm.notes"
              type="text"
              class="ds-input"
              placeholder="Ej. Reposición de estación Cabina 1 desde Bodega General"
            />
          </div>
        </div>
        <div class="ds-modal__footer" style="padding: 0.75rem 0 0; background: transparent">
          <button type="button" class="ds-btn ds-btn--outline" @click="showTransferModal = false">
            Cancelar
          </button>
          <button type="submit" class="ds-btn ds-btn--primary" :disabled="submitting">
            {{ submitting ? 'Transfiriendo...' : 'Ejecutar transferencia' }}
          </button>
        </div>
      </form>
    </ModalDialog>

    <!-- MODAL 5: Tarjeta de Kárdex por Costo Promedio Ponderado (RF-INV-05..07) -->
    <ModalDialog
      v-model="showKardexModal"
      :title="kardexData.product ? `Tarjeta Kárdex · ${kardexData.product.sku} — ${kardexData.product.name}` : 'Tarjeta Kárdex'"
      :subtitle="kardexData.product ? `Método: Costo Promedio Ponderado (NIIF PYMESSección 13) · Cuenta ${kardexData.product.account_code}` : ''"
      size="lg"
    >
      <div v-if="kardexData.product" class="flex-col gap-md">
        <div class="ds-inv-kpi-footbox">
          <span>Existencia actual: <strong>{{ kardexData.product.current_stock }}</strong></span>
          <span>Costo promedio unitario: <strong>${{ kardexData.product.average_cost }}</strong></span>
          <span>Valuación total Kárdex: <strong>${{ kardexData.product.total_valuation }}</strong></span>
        </div>

        <table class="ds-dark-table">
          <thead>
            <tr>
              <th>FECHA</th>
              <th>MOVIMIENTO</th>
              <th>ESTACIÓN</th>
              <th class="text-right">CANTIDAD</th>
              <th class="text-right">COSTO UNIT.</th>
              <th class="text-right">TOTAL ($)</th>
              <th class="text-right">SALDO CANT.</th>
              <th class="text-right">PARTIDA</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in kardexData.movements" :key="m.id">
              <td class="mono">{{ formatDateShort(m.movement_date) }}</td>
              <td>
                <span
                  class="ds-regime-tag"
                  :class="m.direction === 1 ? 'ds-regime-tag--cabina' : 'ds-regime-tag--vitrina'"
                >
                  {{ m.direction === 1 ? 'ENTRADA' : 'SALIDA' }}
                </span>
                <span>{{ m.movement_type_label }}</span>
              </td>
              <td>{{ m.location_name }}</td>
              <td class="text-right mono">{{ m.direction === 1 ? '+' : '-' }}{{ m.quantity }}</td>
              <td class="text-right mono">${{ m.unit_cost }}</td>
              <td class="text-right mono font-bold">${{ m.total_cost }}</td>
              <td class="text-right mono">{{ m.balance_quantity }}</td>
              <td class="text-right">
                <router-link
                  v-if="m.journal_entry_number"
                  :to="`/libro-diario?entry=${m.journal_entry_id}`"
                  class="ds-account-link mono"
                >
                  #{{ m.journal_entry_number }}
                </router-link>
                <span v-else class="text-muted">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </ModalDialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import client from '@/api/http'
import { ExportButton, FormModal as ModalDialog } from '@/components/ui'

const searchVitrina = ref('')
const searchCabina = ref('')
const submitting = ref(false)
const feedbackMsg = ref('')
const errorMsg = ref('')

const summary = ref({
  kpis: {
    vitrina: { items_count: 4, units_total: '61', cost_valuation: '889.50', pvp_valuation: '746.50' },
    cabina: { items_count: 4, units_total: '48', cost_valuation: '551.50', active_stations: 4 },
    critical: { count: 2, suggested_restock: 'Acondicionador & Serum', items: [] },
  },
  vitrina_items: [],
  cabina_items: [],
  locations: [],
  categories: [],
})

const allProducts = computed(() => [
  ...summary.value.vitrina_items,
  ...summary.value.cabina_items,
])

const cabinaLocations = computed(() =>
  summary.value.locations.filter((l) => l.location_type !== 'VITRINA'),
)

async function fetchSummary() {
  try {
    const { data } = await client.get('/v1/inventory/summary/', {
      params: {
        search_vitrina: searchVitrina.value,
        search_cabina: searchCabina.value,
      },
    })
    summary.value = data
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'No se pudo cargar el inventario mixto.'
  }
}

// Modals state
const showProductModal = ref(false)
const showAdjustmentModal = ref(false)
const showConsumptionModal = ref(false)
const showTransferModal = ref(false)
const showKardexModal = ref(false)

const productForm = ref({
  inventory_type: 'VITRINA',
  sku: '',
  name: '',
  brand: '',
  unit_of_measure: 'UNIT',
  sale_price: '15.00',
  average_cost: '8.00',
  min_stock: '5',
  initial_quantity: '0',
})

const adjustmentForm = ref({
  adjustment_date: '2026-11-10',
  reason: 'PHYSICAL_COUNT',
  product_id: null,
  direction: 'OUT',
  quantity: '1',
  notes: '',
})

const consumptionForm = ref({
  consumption_date: '2026-11-10',
  location: 'CAB1',
  product_id: null,
  quantity: '1',
  notes: '',
})

const transferForm = ref({
  transfer_date: '2026-11-10',
  product_id: null,
  from_location: 'GEN',
  to_location: 'CAB1',
  quantity: '1',
  notes: '',
})

const kardexData = ref({ product: null, movements: [] })

function clearMessages() {
  feedbackMsg.value = ''
  errorMsg.value = ''
}

function openProductModal() {
  clearMessages()
  productForm.value = {
    inventory_type: 'VITRINA',
    sku: `VIT-00${summary.value.vitrina_items.length + 1}`,
    name: '',
    brand: '',
    unit_of_measure: 'UNIT',
    sale_price: '15.00',
    average_cost: '8.00',
    min_stock: '5',
    initial_quantity: '0',
  }
  showProductModal.value = true
}

function openAdjustmentModal() {
  clearMessages()
  if (allProducts.value.length) {
    adjustmentForm.value.product_id = allProducts.value[0].id
  }
  showAdjustmentModal.value = true
}

function openConsumptionModal() {
  clearMessages()
  if (summary.value.cabina_items.length) {
    consumptionForm.value.product_id = summary.value.cabina_items[0].id
    consumptionForm.value.location = summary.value.cabina_items[0].location_code || 'CAB1'
  }
  showConsumptionModal.value = true
}

function openTransferModal() {
  clearMessages()
  if (summary.value.cabina_items.length) {
    const first = summary.value.cabina_items[0]
    transferForm.value.product_id = first.id
    transferForm.value.from_location = first.location_code || 'CAB1'
    transferForm.value.to_location = first.location_code === 'CAB1' ? 'CAB2' : 'CAB1'
  }
  showTransferModal.value = true
}

async function openKardexModal(item) {
  clearMessages()
  try {
    const { data } = await client.get(`/v1/inventory/products/${item.id}/kardex/`)
    kardexData.value = data
    showKardexModal.value = true
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'No se pudo cargar el Kárdex del artículo.'
  }
}

async function submitNewProduct() {
  clearMessages()
  submitting.value = true
  try {
    await client.post('/v1/inventory/products/', productForm.value)
    showProductModal.value = false
    feedbackMsg.value = 'Artículo registrado exitosamente en el catálogo de inventario.'
    await fetchSummary()
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || JSON.stringify(err.response?.data || 'Error al crear producto')
  } finally {
    submitting.value = false
  }
}

async function submitAdjustment() {
  clearMessages()
  submitting.value = true
  try {
    const { data } = await client.post('/v1/inventory/adjustments/', {
      adjustment_date: adjustmentForm.value.adjustment_date,
      reason: adjustmentForm.value.reason,
      notes: adjustmentForm.value.notes,
      lines: [
        {
          product_id: adjustmentForm.value.product_id,
          direction: adjustmentForm.value.direction,
          quantity: adjustmentForm.value.quantity,
        },
      ],
    })
    showAdjustmentModal.value = false
    feedbackMsg.value = `Ajuste de stock aplicado y contabilizado en Partida #${data.journal_entry_number || data.id}.`
    await fetchSummary()
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Error al aplicar el ajuste de stock.'
  } finally {
    submitting.value = false
  }
}

async function submitConsumption() {
  clearMessages()
  submitting.value = true
  try {
    const { data } = await client.post('/v1/inventory/consumptions/', {
      consumption_date: consumptionForm.value.consumption_date,
      location: consumptionForm.value.location,
      notes: consumptionForm.value.notes,
      lines: [
        {
          product_id: consumptionForm.value.product_id,
          location: consumptionForm.value.location,
          quantity: consumptionForm.value.quantity,
        },
      ],
    })
    showConsumptionModal.value = false
    feedbackMsg.value = `Consumo de cabina registrado y mayorizado en Partida #${data.journal_entry_number || data.id}.`
    await fetchSummary()
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Error al registrar el consumo de cabina.'
  } finally {
    submitting.value = false
  }
}

async function submitTransfer() {
  clearMessages()
  submitting.value = true
  try {
    await client.post('/v1/inventory/transfers/', {
      transfer_date: transferForm.value.transfer_date,
      product_id: transferForm.value.product_id,
      from_location: transferForm.value.from_location,
      to_location: transferForm.value.to_location,
      quantity: transferForm.value.quantity,
      notes: transferForm.value.notes,
    })
    showTransferModal.value = false
    feedbackMsg.value = 'Transferencia entre ubicaciones ejecutada correctamente en el Kárdex.'
    await fetchSummary()
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Error al transferir existencias.'
  } finally {
    submitting.value = false
  }
}

function formatDateShort(iso) {
  if (!iso) return ''
  const [y, m, d] = iso.slice(0, 10).split('-')
  return `${d}/${m}/${y.slice(2)}`
}

onMounted(() => {
  fetchSummary()
})
</script>
