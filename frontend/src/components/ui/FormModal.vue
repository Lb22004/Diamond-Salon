<script setup>
defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  title: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    default: '',
  },
  size: {
    type: String,
    default: 'md', // 'sm' | 'md' | 'lg'
  },
  submitLabel: {
    type: String,
    default: 'Guardar',
  },
  cancelLabel: {
    type: String,
    default: 'Cancelar',
  },
  loading: {
    type: Boolean,
    default: false,
  },
  hideFooter: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'submit', 'close'])

function close() {
  emit('update:modelValue', false)
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div v-if="modelValue" class="ds-modal-backdrop" @click.self="close">
      <div
        class="ds-modal"
        :class="`ds-modal--${size}`"
        role="dialog"
        aria-modal="true"
      >
        <header class="ds-modal__header">
          <div>
            <h3 class="ds-modal__title">{{ title }}</h3>
            <p v-if="subtitle" class="ds-modal__subtitle">{{ subtitle }}</p>
          </div>
          <button type="button" class="ds-modal__close" aria-label="Cerrar" @click="close">
            ×
          </button>
        </header>

        <form class="ds-modal__form" @submit.prevent="emit('submit')">
          <div class="ds-modal__body">
            <slot />
          </div>

          <footer v-if="!hideFooter" class="ds-modal__footer">
            <slot name="footer">
              <button type="button" class="ds-btn ds-btn--ghost" @click="close">
                {{ cancelLabel }}
              </button>
              <button type="submit" class="ds-btn ds-btn--primary" :disabled="loading">
                {{ loading ? 'Guardando…' : submitLabel }}
              </button>
            </slot>
          </footer>
        </form>
      </div>
    </div>
  </Teleport>
</template>
