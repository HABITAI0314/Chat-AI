<script setup lang="ts">
defineProps<{
  modelValue: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  send: []
  transfer: []
}>()

const onKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    emit('send')
  }
}
</script>

<template>
  <div class="composer">
    <textarea
      :value="modelValue"
      :disabled="disabled"
      rows="1"
      placeholder="说点什么…"
      @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
      @keydown="onKeydown"
    />
    <button
      class="transfer-button"
      type="button"
      :disabled="disabled"
      title="发送模拟转账"
      @click="emit('transfer')"
    >
      <span>＋</span>
      <span>转账</span>
    </button>
    <button class="send-button" type="button" :disabled="disabled || !modelValue.trim()" @click="emit('send')">
      <span>发送</span>
      <span>↗</span>
    </button>
  </div>
</template>
