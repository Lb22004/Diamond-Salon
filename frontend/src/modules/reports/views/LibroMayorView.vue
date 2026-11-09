<template>
  <div class="flex-col gap-lg">
    <!-- Top Header -->
    <div class="page-header flex-between" style="flex-wrap: wrap; gap: 16px">
      <div>
        <div class="eyebrow">CONTABILIDAD · MAYORIZACIÓN Y ESTADOS FINANCIEROS</div>
        <h1 class="page-title">Libro Mayor, Balance y Cierre Mensual</h1>
        <p class="page-subtitle">
          Saldos acumulados en tiempo real, resumen mayorizado simultáneo, balance de comprobación y estados financieros NIIF.
        </p>
      </div>

      <div class="flex-row gap-sm" style="flex-wrap: wrap">
        <button
          type="button"
          class="btn btn--secondary"
          @click="showCloseModal = true"
        >
          <span>{{ periodStore.isPeriodOpen ? '🔒 Cerrar Período' : '🔐 Ver Cierre Mensual' }}</span>
        </button>
        <ExportButton
          :book="exportBookKey"
          :params="exportParams"
          label="Exportar Reporte"
        />
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="tabs-bar flex-between" style="border-bottom: 1px solid var(--border-soft); padding-bottom: 10px; flex-wrap: wrap; gap: 12px">
      <div class="flex-row gap-xs">
        <button
          type="button"
          class="btn"
          :class="activeTab === 'ledger' ? 'btn--primary' : 'btn--ghost'"
          @click="activeTab = 'ledger'"
        >
          Libro Mayor Analítico
        </button>
        <button
          type="button"
          class="btn"
          :class="activeTab === 'trial-balance' ? 'btn--primary' : 'btn--ghost'"
          @click="switchTab('trial-balance')"
        >
          Balance de Comprobación
        </button>
        <button
          type="button"
          class="btn"
          :class="activeTab === 'financial-statements' ? 'btn--primary' : 'btn--ghost'"
          @click="switchTab('financial-statements')"
        >
          Estados Financieros NIIF
        </button>
      </div>

      <div class="flex-row gap-sm">
        <Badge :variant="ledgerData.verification?.trial_balance_ok !== false ? 'success' : 'danger'">
          {{ ledgerData.verification?.trial_balance_ok !== false ? '✓ Sumas iguales verificadas: OK' : '⚠ Descuadre detectado' }}
        </Badge>
      </div>
    </div>

    <!-- ==================== TAB 1: LIBRO MAYOR ANALÍTICO ==================== -->
    <template v-if="activeTab === 'ledger'">
      <!-- Filter Bar: Account Selector + Date Range + Quick Chips (RF-MAY-01, RF-MAY-02) -->
      <div class="card p-md flex-col gap-md">
        <div class="flex-between" style="flex-wrap: wrap; gap: 14px">
          <div class="flex-row gap-sm" style="flex: 1; min-width: 280px">
            <label class="text-muted" style="font-size: 12px; font-weight: 600; white-space: nowrap">
              Cuenta Mayor:
            </label>
            <select
              v-model="selectedAccountCode"
              class="form-select"
              style="max-width: 440px"
              @change="fetchLedger"
            >
              <option
                v-for="acc in allAccounts"
                :key="acc.id"
                :value="acc.code"
              >
                {{ acc.code }} — {{ acc.name }} ({{ acc.nature === 'DEBIT' ? 'Deudora' : 'Acreedora' }}{{ !acc.accepts_entries ? ' · Agrupadora' : '' }})
              </option>
            </select>
          </div>

          <DateRangePicker
            v-model:from="dateFrom"
            v-model:to="dateTo"
            @change="fetchLedger"
          />
        </div>

        <!-- Quick Salon Accounts Chips -->
        <div class="flex-row gap-xs" style="flex-wrap: wrap; align-items: center">
          <span class="eyebrow" style="margin-right: 4px">ACCESO RÁPIDO:</span>
          <button
            v-for="chip in quickAccountChips"
            :key="chip.code"
            type="button"
            class="chip"
            :class="{ 'chip--active': selectedAccountCode === chip.code }"
            @click="selectAccount(chip.code)"
          >
            <span class="mono" style="font-weight: 600">{{ chip.code }}</span>
            <span>· {{ chip.label }}</span>
          </button>
        </div>
      </div>

      <!-- Selected Account Header Banner (RF-MAY-03) -->
      <div v-if="ledgerData.account" class="card p-md flex-between" style="background: var(--bg-subtle); flex-wrap: wrap; gap: 12px">
        <div class="flex-row gap-md" style="align-items: center">
          <div
            class="mono"
            style="background: var(--color-ink); color: var(--color-ivory); padding: 8px 14px; border-radius: 8px; font-size: 16px; font-weight: 700"
          >
            {{ ledgerData.account.code }}
          </div>
          <div>
            <div style="font-family: var(--font-display); font-size: 20px; font-weight: 600">
              {{ ledgerData.account.name }}
            </div>
            <div class="text-muted" style="font-size: 12.5px">
              {{ ledgerData.account.classification || ledgerData.account.level_label }} · Nivel {{ ledgerData.account.level }}
            </div>
          </div>
        </div>

        <div class="flex-row gap-xs">
          <Badge :variant="ledgerData.account.nature === 'DEBIT' ? 'info' : 'warning'">
            Naturaleza {{ ledgerData.account.nature_label || (ledgerData.account.nature === 'DEBIT' ? 'Deudora' : 'Acreedora') }}
          </Badge>
          <Badge v-if="ledgerData.account.inventory_type && ledgerData.account.inventory_type !== 'NONE'" variant="accent">
            Inventario {{ ledgerData.account.inventory_type }}
          </Badge>
          <Badge variant="neutral">
            {{ ledgerData.movements?.length || 0 }} movimiento(s)
          </Badge>
        </div>
      </div>

      <!-- 4 KPI Cards (RF-MAY-04) -->
      <div class="kpi-grid">
        <KpiCard
          title="APERTURA / BASE INICIAL"
          :value="ledgerData.kpis?.effective_initial_balance || '0.00'"
          :subtitle="`Saldo anterior al corte: ${formatMoney(ledgerData.kpis?.opening_balance || '0.00')}`"
          badge="Base Inicial"
          badge-variant="neutral"
        />
        <KpiCard
          title="TOTAL CARGOS (DEBE)"
          :value="ledgerData.kpis?.debit_total || '0.00'"
          :subtitle="`${ledgerData.kpis?.debit_count || 0} cargo(s) mayorizados en el período`"
          badge="Cargos"
          badge-variant="gold"
          tone="gold"
        />
        <KpiCard
          title="TOTAL ABONOS (HABER)"
          :value="ledgerData.kpis?.credit_total || '0.00'"
          :subtitle="`${ledgerData.kpis?.credit_count || 0} abono(s) mayorizados en el período`"
          badge="Abonos"
          badge-variant="wine"
        />
        <KpiCard
          title="SALDO DE CIERRE ACTUAL"
          :value="ledgerData.kpis?.closing_balance || '0.00'"
          :subtitle="`Variación neta: ${ledgerData.kpis?.variation_pct || '+0.00%'}`"
          :badge="ledgerData.kpis?.variation_pct || '+0.00%'"
          badge-variant="gold"
          tone="ink"
        />
      </div>

      <!-- Main 2-Column Grid: Chronological Movements Table + Evolution Donut (RF-MAY-05..07) -->
      <div class="ledger-main-grid" style="display: grid; grid-template-columns: minmax(0, 2.2fr) minmax(290px, 1fr); gap: 20px; align-items: start">
        <!-- Movements Table -->
        <div class="card p-0" style="overflow: hidden">
          <div class="p-md flex-between" style="border-bottom: 1px solid var(--border-soft)">
            <div>
              <div class="eyebrow">DETALLE CRONOLÓGICO DE MAYORIZACIÓN (RF-MAY-05)</div>
              <h3 style="margin: 2px 0 0; font-size: 16px">Movimientos y Saldo Acumulado Línea por Línea</h3>
            </div>
            <span class="text-muted" style="font-size: 12px">
              Del {{ ledgerData.date_from }} al {{ ledgerData.date_to }}
            </span>
          </div>

          <div style="overflow-x: auto">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Ref. Diario</th>
                  <th>Tipo</th>
                  <th>Concepto / Glosa Contable</th>
                  <th class="text-right">Cargo (Debe)</th>
                  <th class="text-right">Abono (Haber)</th>
                  <th class="text-right">Saldo Resultante</th>
                </tr>
              </thead>
              <tbody>
                <!-- Sticky Opening Balance Row -->
                <tr style="background: var(--bg-subtle); font-weight: 600">
                  <td class="mono">{{ ledgerData.date_from }}</td>
                  <td><Badge variant="neutral">SALDO INIC.</Badge></td>
                  <td class="text-muted">Apertura</td>
                  <td>Saldo acumulado anterior al rango consultado</td>
                  <td class="text-right mono text-muted">$0.00</td>
                  <td class="text-right mono text-muted">$0.00</td>
                  <td class="text-right mono">{{ formatMoney(ledgerData.kpis?.opening_balance || '0.00') }}</td>
                </tr>

                <tr v-if="!ledgerData.movements?.length">
                  <td colspan="7" class="text-center text-muted p-lg">
                    No se registran movimientos mayorizados para esta cuenta en el rango seleccionado.
                  </td>
                </tr>

                <tr
                  v-for="mov in ledgerData.movements"
                  :key="mov.line_id"
                >
                  <td class="mono">{{ mov.entry_date }}</td>
                  <td>
                    <router-link
                      :to="{ path: '/diario', query: { entry: mov.entry_id } }"
                      class="mono"
                      style="color: var(--color-gold-deep); font-weight: 600; text-decoration: none"
                    >
                      {{ mov.entry_ref }} ↗
                    </router-link>
                  </td>
                  <td>
                    <Badge :variant="mov.entry_type === 'OPENING' ? 'accent' : mov.entry_type === 'CLOSING' ? 'warning' : 'neutral'">
                      {{ mov.entry_type_label }}
                    </Badge>
                  </td>
                  <td>{{ mov.concept }}</td>
                  <td class="text-right">
                    <MoneyCell :value="mov.debit" />
                  </td>
                  <td class="text-right">
                    <MoneyCell :value="mov.credit" />
                  </td>
                  <td class="text-right" style="font-weight: 600">
                    <MoneyCell :value="mov.resulting_balance" />
                  </td>
                </tr>
              </tbody>
              <!-- Totals Footer Row (RF-MAY-06) -->
              <tfoot>
                <tr style="background: var(--bg-subtle); font-weight: 700; border-top: 2px solid var(--border-strong)">
                  <td colspan="4">SUMAS DEL PERÍODO Y SALDO DE CIERRE</td>
                  <td class="text-right mono">{{ formatMoney(ledgerData.kpis?.debit_total || '0.00') }}</td>
                  <td class="text-right mono">{{ formatMoney(ledgerData.kpis?.credit_total || '0.00') }}</td>
                  <td class="text-right mono" style="color: var(--color-gold-deep)">
                    {{ formatMoney(ledgerData.kpis?.closing_balance || '0.00') }}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        <!-- Evolution Donut Card (RF-MAY-07) -->
        <div class="card p-md flex-col gap-md">
          <div>
            <div class="eyebrow"> COMPOSICIÓN DEL FLUJO (RF-MAY-07)</div>
            <h3 style="margin: 2px 0 0; font-size: 16px">Evolución de la Cuenta</h3>
          </div>

          <div class="flex-col" style="align-items: center; padding: 10px 0">
            <svg width="200" height="200" viewBox="0 0 200 200">
              <circle
                cx="100"
                cy="100"
                r="74"
                fill="none"
                stroke="#EFE9DF"
                stroke-width="22"
              />
              <circle
                v-for="(seg, idx) in donutSegments"
                :key="idx"
                cx="100"
                cy="100"
                r="74"
                fill="none"
                :stroke="seg.color"
                stroke-width="22"
                :stroke-dasharray="`${seg.length} ${donutCircumference - seg.length}`"
                :stroke-dashoffset="-seg.offset"
                transform="rotate(-90 100 100)"
              />
              <text x="100" y="92" text-anchor="middle" fill="#6E655C" font-size="10" font-weight="600">
                SALDO FINAL
              </text>
              <text x="100" y="114" text-anchor="middle" fill="#1E1B18" font-size="15" font-weight="700">
                {{ formatMoney(ledgerData.kpis?.closing_balance || '0.00') }}
              </text>
            </svg>
          </div>

          <div class="flex-col gap-xs" style="font-size: 12.5px">
            <div class="flex-between p-xs" style="border-bottom: 1px solid var(--border-soft)">
              <span class="flex-row gap-xs" style="align-items: center">
                <span style="width: 10px; height: 10px; border-radius: 50%; background: #C8A97E; display: inline-block"></span>
                <span>Base Inicial / Apertura</span>
              </span>
              <span class="mono" style="font-weight: 600">{{ formatMoney(ledgerData.kpis?.effective_initial_balance || '0.00') }}</span>
            </div>
            <div class="flex-between p-xs" style="border-bottom: 1px solid var(--border-soft)">
              <span class="flex-row gap-xs" style="align-items: center">
                <span style="width: 10px; height: 10px; border-radius: 50%; background: #2E6B4E; display: inline-block"></span>
                <span>Entradas / Flujo Operativo</span>
              </span>
              <span class="mono" style="font-weight: 600">{{ formatMoney(ledgerData.kpis?.operational_inflow || '0.00') }}</span>
            </div>
            <div class="flex-between p-xs">
              <span class="flex-row gap-xs" style="align-items: center">
                <span style="width: 10px; height: 10px; border-radius: 50%; background: #A63A3A; display: inline-block"></span>
                <span>Salidas / Abonos</span>
              </span>
              <span class="mono" style="font-weight: 600">{{ formatMoney(ledgerData.kpis?.credit_total || '0.00') }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Simultaneous Majorized Summary (RF-MAY-08) -->
      <div class="card p-md flex-col gap-md">
        <div class="flex-between">
          <div>
            <div class="eyebrow">PANORAMA CONTABLE MULTICUENTA (RF-MAY-08)</div>
            <h3 style="margin: 2px 0 0; font-size: 16px">Resumen Mayorizado Simultáneo de Cuentas Clave</h3>
          </div>
          <span class="text-muted" style="font-size: 12px">
            Haga clic en cualquier tarjeta para inspeccionar su Libro Mayor
          </span>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(245px, 1fr)); gap: 12px">
          <div
            v-for="item in ledgerData.simultaneous_summary"
            :key="item.code"
            class="card p-md"
            style="cursor: pointer; transition: all 0.15s ease"
            :style="{
              borderColor: selectedAccountCode === item.code ? 'var(--color-gold)' : 'var(--border-soft)',
              background: selectedAccountCode === item.code ? 'rgba(200, 169, 126, 0.08)' : 'var(--bg-surface)'
            }"
            @click="selectAccount(item.code)"
          >
            <div class="flex-between mb-xs">
              <span class="mono" style="font-weight: 700; font-size: 13px; color: var(--color-gold-deep)">
                {{ item.code }}
              </span>
              <Badge :variant="item.nature === 'DEBIT' ? 'info' : 'warning'">
                {{ item.nature === 'DEBIT' ? 'Deudora' : 'Acreedora' }}
              </Badge>
            </div>
            <div style="font-weight: 600; font-size: 14px; margin-bottom: 6px">
              {{ item.name }}
            </div>
            <div style="font-family: var(--font-display); font-size: 20px; font-weight: 700; margin-bottom: 6px">
              {{ formatMoney(item.balance) }}
            </div>
            <div class="flex-between text-muted" style="font-size: 11.5px">
              <span>D: {{ formatMoney(item.debit_total) }} · H: {{ formatMoney(item.credit_total) }}</span>
              <span>{{ item.movements_count }} mov.</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ==================== TAB 2: BALANCE DE COMPROBACIÓN ==================== -->
    <template v-else-if="activeTab === 'trial-balance'">
      <div class="card p-0" style="overflow: hidden">
        <div class="p-md flex-between" style="border-bottom: 1px solid var(--border-soft)">
          <div>
            <div class="eyebrow">VERIFICACIÓN DE PARTIDA DOBLE (RF-MAY-10)</div>
            <h3 style="margin: 2px 0 0; font-size: 17px">
              Balance de Comprobación de Sumas y Saldos · {{ trialBalance.period?.label || periodStore.activePeriodLabel }}
            </h3>
          </div>
          <Badge :variant="trialBalance.totals?.is_balanced ? 'success' : 'danger'">
            {{ trialBalance.totals?.is_balanced ? '✓ Sumas y Saldos Cuadrados' : '⚠ Diferencia Detectada' }}
          </Badge>
        </div>

        <div style="overflow-x: auto">
          <table class="data-table">
            <thead>
              <tr>
                <th>Código</th>
                <th>Nombre de Cuenta</th>
                <th>Rubro</th>
                <th>Naturaleza</th>
                <th class="text-right">Saldo Inicial</th>
                <th class="text-right">Cargos (Debe)</th>
                <th class="text-right">Abonos (Haber)</th>
                <th class="text-right">Saldo Deudor</th>
                <th class="text-right">Saldo Acreedor</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in trialBalance.rows"
                :key="row.code"
                style="cursor: pointer"
                @click="inspectAccountFromTable(row.code)"
              >
                <td class="mono" style="font-weight: 600; color: var(--color-gold-deep)">{{ row.code }}</td>
                <td style="font-weight: 500">{{ row.name }}</td>
                <td><Badge variant="neutral">{{ row.account_type_label }}</Badge></td>
                <td>
                  <Badge :variant="row.nature === 'DEBIT' ? 'info' : 'warning'">
                    {{ row.nature_label }}
                  </Badge>
                </td>
                <td class="text-right"><MoneyCell :value="row.opening_balance" /></td>
                <td class="text-right"><MoneyCell :value="row.debit_total" /></td>
                <td class="text-right"><MoneyCell :value="row.credit_total" /></td>
                <td class="text-right" style="font-weight: 600"><MoneyCell :value="row.closing_debit" /></td>
                <td class="text-right" style="font-weight: 600"><MoneyCell :value="row.closing_credit" /></td>
              </tr>
            </tbody>
            <tfoot v-if="trialBalance.totals">
              <tr style="background: var(--bg-subtle); font-weight: 700; border-top: 2px solid var(--border-strong)">
                <td colspan="4">SUMAS IGUALES DEL BALANCE DE COMPROBACIÓN</td>
                <td class="text-right mono">$0.00</td>
                <td class="text-right mono">{{ formatMoney(trialBalance.totals.debit_total) }}</td>
                <td class="text-right mono">{{ formatMoney(trialBalance.totals.credit_total) }}</td>
                <td class="text-right mono" style="color: var(--color-success)">
                  {{ formatMoney(trialBalance.totals.closing_debit) }}
                </td>
                <td class="text-right mono" style="color: var(--color-success)">
                  {{ formatMoney(trialBalance.totals.closing_credit) }}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </template>

    <!-- ==================== TAB 3: ESTADOS FINANCIEROS NIIF ==================== -->
    <template v-else-if="activeTab === 'financial-statements'">
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 20px; align-items: start">
        <!-- Estado de Resultados (RF-REP-02) -->
        <div class="card p-md flex-col gap-md">
          <div class="flex-between" style="border-bottom: 1px solid var(--border-soft); padding-bottom: 10px">
            <div>
              <div class="eyebrow">DESEMPEÑO ECONÓMICO (RF-REP-02)</div>
              <h3 style="margin: 2px 0 0; font-size: 17px">Estado de Resultados Integral</h3>
            </div>
            <Badge variant="accent">{{ financialStatements.period?.label || periodStore.activePeriodLabel }}</Badge>
          </div>

          <!-- Ingresos -->
          <div>
            <div class="eyebrow mb-xs">5 · INGRESOS DE ACTIVIDADES ORDINARIAS</div>
            <table class="data-table">
              <tbody>
                <tr v-for="item in financialStatements.income_statement?.incomes" :key="item.code">
                  <td class="mono" style="width: 85px">{{ item.code }}</td>
                  <td>{{ item.name }}</td>
                  <td class="text-right mono">{{ formatMoney(item.balance) }}</td>
                </tr>
                <tr style="font-weight: 700; background: var(--bg-subtle)">
                  <td colspan="2">TOTAL INGRESOS OPERATIVOS</td>
                  <td class="text-right mono">{{ formatMoney(financialStatements.income_statement?.total_income) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Costos -->
          <div>
            <div class="eyebrow mb-xs">41 · COSTO DE VENTAS Y CONSUMO DE INSUMOS DE CABINA</div>
            <table class="data-table">
              <tbody>
                <tr v-for="item in financialStatements.income_statement?.costs" :key="item.code">
                  <td class="mono" style="width: 85px">{{ item.code }}</td>
                  <td>{{ item.name }}</td>
                  <td class="text-right mono">{{ formatMoney(item.balance) }}</td>
                </tr>
                <tr style="font-weight: 700; background: var(--bg-subtle)">
                  <td colspan="2">TOTAL COSTOS DIRECTOS</td>
                  <td class="text-right mono">{{ formatMoney(financialStatements.income_statement?.total_cost) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="card p-sm flex-between" style="background: var(--bg-subtle); font-weight: 700">
            <span>UTILIDAD BRUTA EN OPERACIONES</span>
            <span class="mono" style="font-size: 15px">{{ formatMoney(financialStatements.income_statement?.gross_profit) }}</span>
          </div>

          <!-- Gastos -->
          <div>
            <div class="eyebrow mb-xs">42 · GASTOS OPERATIVOS Y DE ADMINISTRACIÓN</div>
            <table class="data-table">
              <tbody>
                <tr v-if="!financialStatements.income_statement?.expenses?.length">
                  <td colspan="3" class="text-muted text-center">Sin gastos administrativos registrados en el período</td>
                </tr>
                <tr v-for="item in financialStatements.income_statement?.expenses" :key="item.code">
                  <td class="mono" style="width: 85px">{{ item.code }}</td>
                  <td>{{ item.name }}</td>
                  <td class="text-right mono">{{ formatMoney(item.balance) }}</td>
                </tr>
                <tr style="font-weight: 700; background: var(--bg-subtle)">
                  <td colspan="2">TOTAL GASTOS DE OPERACIÓN</td>
                  <td class="text-right mono">{{ formatMoney(financialStatements.income_statement?.total_expense) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="card p-md flex-between" style="background: var(--color-ink); color: var(--color-ivory)">
            <div>
              <div class="eyebrow" style="color: var(--color-gold)">RESULTADO DEL PERÍODO</div>
              <div style="font-weight: 700; font-size: 15px">UTILIDAD / EXCEDENTE NETO DEL EJERCICIO</div>
            </div>
            <div class="mono" style="font-size: 20px; font-weight: 700; color: var(--color-gold)">
              {{ formatMoney(financialStatements.income_statement?.net_income) }}
            </div>
          </div>
        </div>

        <!-- Balance General (RF-REP-03) -->
        <div class="card p-md flex-col gap-md">
          <div class="flex-between" style="border-bottom: 1px solid var(--border-soft); padding-bottom: 10px">
            <div>
              <div class="eyebrow">POSICIÓN PATRIMONIAL (RF-REP-03)</div>
              <h3 style="margin: 2px 0 0; font-size: 17px">Estado de Situación Financiera (Balance General)</h3>
            </div>
            <Badge :variant="financialStatements.balance_sheet?.is_balanced ? 'success' : 'danger'">
              {{ financialStatements.balance_sheet?.is_balanced ? '✓ Activo = Pasivo + Patrimonio' : '⚠ Revisar' }}
            </Badge>
          </div>

          <!-- Activos -->
          <div>
            <div class="eyebrow mb-xs">1 · ACTIVOS (CORRIENTES Y NO CORRIENTES)</div>
            <table class="data-table">
              <tbody>
                <tr v-for="item in financialStatements.balance_sheet?.assets" :key="item.code">
                  <td class="mono" style="width: 85px">{{ item.code }}</td>
                  <td>{{ item.name }}</td>
                  <td class="text-right mono">{{ formatMoney(item.balance) }}</td>
                </tr>
                <tr style="font-weight: 700; background: var(--bg-subtle)">
                  <td colspan="2">TOTAL ACTIVOS</td>
                  <td class="text-right mono">{{ formatMoney(financialStatements.balance_sheet?.total_assets) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Pasivos -->
          <div>
            <div class="eyebrow mb-xs">2 · PASIVOS Y OBLIGACIONES</div>
            <table class="data-table">
              <tbody>
                <tr v-for="item in financialStatements.balance_sheet?.liabilities" :key="item.code">
                  <td class="mono" style="width: 85px">{{ item.code }}</td>
                  <td>{{ item.name }}</td>
                  <td class="text-right mono">{{ formatMoney(item.balance) }}</td>
                </tr>
                <tr style="font-weight: 700; background: var(--bg-subtle)">
                  <td colspan="2">TOTAL PASIVOS</td>
                  <td class="text-right mono">{{ formatMoney(financialStatements.balance_sheet?.total_liabilities) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Patrimonio -->
          <div>
            <div class="eyebrow mb-xs">3 · PATRIMONIO NETO</div>
            <table class="data-table">
              <tbody>
                <tr v-for="item in financialStatements.balance_sheet?.equity" :key="item.code">
                  <td class="mono" style="width: 85px">{{ item.code }}</td>
                  <td>{{ item.name }}</td>
                  <td class="text-right mono">{{ formatMoney(item.balance) }}</td>
                </tr>
                <tr>
                  <td class="mono" style="width: 85px">320102</td>
                  <td>Resultado del Ejercicio Actual</td>
                  <td class="text-right mono">{{ formatMoney(financialStatements.balance_sheet?.current_period_result) }}</td>
                </tr>
                <tr style="font-weight: 700; background: var(--bg-subtle)">
                  <td colspan="2">TOTAL PATRIMONIO NETO</td>
                  <td class="text-right mono">{{ formatMoney(financialStatements.balance_sheet?.total_equity) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="card p-md flex-between" style="background: var(--color-ink); color: var(--color-ivory)">
            <div>
              <div class="eyebrow" style="color: var(--color-gold)">ECUACIÓN CONTABLE FUNDAMENTAL</div>
              <div style="font-weight: 700; font-size: 15px">TOTAL PASIVO + PATRIMONIO</div>
            </div>
            <div class="mono" style="font-size: 20px; font-weight: 700; color: var(--color-gold)">
              {{ formatMoney(financialStatements.balance_sheet?.total_liabilities_and_equity) }}
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Monthly Closing Modal (RF-CIE-01..05) -->
    <PeriodCloseModal
      v-model="showCloseModal"
      @closed="refreshAllData"
      @reopened="refreshAllData"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import http from '@/api/http'
import { usePeriodStore } from '@/stores/period'
import { formatMoney } from '@/utils/formatters'
import { Badge, DateRangePicker, ExportButton, KpiCard, MoneyCell } from '@/components/ui'
import PeriodCloseModal from '../components/PeriodCloseModal.vue'

const route = useRoute()
const periodStore = usePeriodStore()

const activeTab = ref('ledger')
const showCloseModal = ref(false)
const allAccounts = ref([])
const selectedAccountCode = ref('110101')
const dateFrom = ref('')
const dateTo = ref('')

const ledgerData = ref({
  account: null,
  kpis: {},
  verification: { trial_balance_ok: true },
  movements: [],
  simultaneous_summary: [],
})

const trialBalance = ref({
  period: null,
  rows: [],
  totals: null,
})

const financialStatements = ref({
  period: null,
  income_statement: null,
  balance_sheet: null,
})

const quickAccountChips = [
  { code: '110101', label: 'Caja general' },
  { code: '110102', label: 'Bancos' },
  { code: '110501', label: 'Mercadería Vitrina' },
  { code: '110502', label: 'Insumos Cabina' },
  { code: '110601', label: 'IVA Crédito' },
  { code: '2107', label: 'IVA Débito' },
  { code: '210101', label: 'Proveedores' },
  { code: '5101', label: 'Ingresos Servicios' },
  { code: '5102', label: 'Ingresos Productos' },
]

const exportBookKey = computed(() => {
  if (activeTab.value === 'trial-balance') return 'trial-balance'
  if (activeTab.value === 'financial-statements') return 'financial-statements'
  return 'ledger'
})

const exportParams = computed(() => {
  const params = {}
  if (periodStore.activePeriod?.id) {
    params.period = periodStore.activePeriod.id
  }
  if (activeTab.value === 'ledger') {
    params.account = selectedAccountCode.value
    if (dateFrom.value) params.date_from = dateFrom.value
    if (dateTo.value) params.date_to = dateTo.value
  }
  return params
})

const donutCircumference = 2 * Math.PI * 74
const donutSegments = computed(() => {
  const initVal = Math.max(0, Number(ledgerData.value.kpis?.effective_initial_balance || 0))
  const inVal = Math.max(0, Number(ledgerData.value.kpis?.operational_inflow || 0))
  const outVal = Math.max(0, Number(ledgerData.value.kpis?.credit_total || 0))
  const total = initVal + inVal + outVal
  if (total <= 0) return []

  const items = [
    { val: initVal, color: '#C8A97E' },
    { val: inVal, color: '#2E6B4E' },
    { val: outVal, color: '#A63A3A' },
  ]
  let offset = 0
  return items.map((item) => {
    const length = (item.val / total) * donutCircumference
    const seg = { color: item.color, length, offset }
    offset += length
    return seg
  })
})

async function fetchAccountsList() {
  try {
    const { data } = await http.get('/v1/accounts/', { params: { flat: 1 } })
    allAccounts.value = Array.isArray(data) ? data : data.results || []
  } catch {
    allAccounts.value = []
  }
}

async function fetchLedger() {
  try {
    const params = { account: selectedAccountCode.value }
    if (periodStore.activePeriod?.id) params.period = periodStore.activePeriod.id
    if (dateFrom.value) params.date_from = dateFrom.value
    if (dateTo.value) params.date_to = dateTo.value
    const { data } = await http.get('/v1/ledger/', { params })
    ledgerData.value = data
    if (!dateFrom.value && data.date_from) dateFrom.value = data.date_from
    if (!dateTo.value && data.date_to) dateTo.value = data.date_to
  } catch {
    // fallback handled gracefully
  }
}

async function fetchTrialBalance() {
  try {
    const params = {}
    if (periodStore.activePeriod?.id) params.period = periodStore.activePeriod.id
    const { data } = await http.get('/v1/trial-balance/', { params })
    trialBalance.value = data
  } catch {
    // ignore
  }
}

async function fetchFinancialStatements() {
  try {
    const params = {}
    if (periodStore.activePeriod?.id) params.period = periodStore.activePeriod.id
    const { data } = await http.get('/v1/financial-statements/', { params })
    financialStatements.value = data
  } catch {
    // ignore
  }
}

function selectAccount(code) {
  selectedAccountCode.value = code
  fetchLedger()
}

function inspectAccountFromTable(code) {
  selectedAccountCode.value = code
  activeTab.value = 'ledger'
  fetchLedger()
}

function switchTab(tab) {
  activeTab.value = tab
  if (tab === 'trial-balance') fetchTrialBalance()
  if (tab === 'financial-statements') fetchFinancialStatements()
}

async function refreshAllData() {
  await Promise.all([fetchLedger(), fetchTrialBalance(), fetchFinancialStatements()])
}

watch(
  () => periodStore.activePeriod?.id,
  () => {
    dateFrom.value = ''
    dateTo.value = ''
    refreshAllData()
  }
)

onMounted(async () => {
  if (route.query.account) {
    selectedAccountCode.value = String(route.query.account)
  }
  if (route.query.tab) {
    activeTab.value = String(route.query.tab)
  }
  await fetchAccountsList()
  await refreshAllData()
})
</script>
