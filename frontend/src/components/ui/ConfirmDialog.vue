<script setup>
import { ref, watch } from 'vue'
import FormModal from './FormModal.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  title: {
    type: String,
    default: 'Confirmar acción',
  },
  message: {
    type: String,
    default: '¿Está seguro de que desea continuar?',
  },
  confirmLabel: {
    type: String,
    default: 'Confirmar',
  },
  requireReason: {
    type: Boolean,
    default: false,
  },
  reasonPlaceholder: {
    type: String,
    default: 'Indique el motivo de esta acción para la bitácora de auditoría…',
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'confirm'])
const reason = ref('')
const error = ref('')

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      reason.value = ''
      error.value = ''
    }
  }
)

function onSubmit() {
  if (props.requireReason && reason.value.trim().length < 5) {
    error.value = 'Debe ingresar un motivo válido (mínimo 5 caracteres).'
    return
  }
  emit('confirm', reason.value.trim())
}
</script>

<template>
  <FormModal
    :model-value="modelValue"
    :title="title"
    size="sm"
    :submit-label="confirmLabel"
    :loading="loading"
    @update:model-value="emit('update:modelValue', $event)"
    @submit="onSubmit"
  >
    <p class="ds-confirm-msg">{{ message }}</p>

    <div v-if="requireReason" class="ds-field">
      <label class="ds-field__label">Motivo obligatorio (Auditoría)</label>
      <textarea
        v-model="reason"
        rows="3"
        class="ds-input"
        :placeholder="reasonPlaceholder"
        required
      />
      <p v-if="error" class="ds-field__error">{{ error }}</p>
    </div>
  </FormModal>
</template>
