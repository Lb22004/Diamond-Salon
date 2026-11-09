<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  placeholder: {
    type: String,
    default: 'Buscar…',
  },
  debounce: {
    type: Number,
    default: 200,
  },
})

const emit = defineEmits(['update:modelValue', 'search'])
const localValue = ref(props.modelValue)
let timer = null

watch(
  () => props.modelValue,
  (val) => {
    if (val !== localValue.value) localValue.value = val
  }
)

function onInput(event) {
  const val = event.target.value
  localValue.value = val
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => {
    emit('update:modelValue', val)
    emit('search', val)
  }, props.debounce)
}

function clear() {
  localValue.value = ''
  if (timer) clearTimeout(timer)
  emit('update:modelValue', '')
  emit('search', '')
}

onBeforeUnmount(() => {
  if (timer) clearTimeout(timer)
})
</script>

<template>
  <div class="ds-search-input">
    <span class="ds-search-input__icon" aria-hidden="true">
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
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
    </span>
    <input
      type="search"
      :value="localValue"
      :placeholder="placeholder"
      class="ds-input"
      @input="onInput"
    />
    <button
      v-if="localValue"
      type="button"
      class="ds-search-input__clear"
      title="Limpiar búsqueda"
      @click="clear"
    >
      ×
    </button>
  </div>
</template>
