<script setup>
import { RouterLink, RouterView } from 'vue-router'

const menu = [
  { to: '/panel', label: 'Panel' },
  { to: '/catalogo-cuentas', label: 'Catálogo de cuentas' },
  { to: '/inventario', label: 'Inventario' },
  { to: '/libro-ventas', label: 'Libro de ventas' },
  { to: '/libro-compras', label: 'Libro de compras' },
  { to: '/libro-diario', label: 'Libro diario' },
  { to: '/libro-mayor', label: 'Libro mayor' },
]
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">Diamond Salón<small>ATELIER CONTABLE</small></div>
      <p class="section">LIBROS &amp; OPERACIONES</p>
      <nav>
        <RouterLink v-for="item in menu" :key="item.to" :to="item.to">{{ item.label }}</RouterLink>
      </nav>
    </aside>
    <main class="content">
      <RouterView />
    </main>
  </div>
</template>
