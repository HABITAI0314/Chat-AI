<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  characterName?: string
  disabled?: boolean
  submitting?: boolean
}>()

const emit = defineEmits<{
  close: []
  confirm: [amountCents: number, note: string]
}>()

const amount = ref('8.88')
const note = ref('')

const amountCents = computed(() => {
  const value = Number(amount.value)
  if (!Number.isFinite(value) || value <= 0 || value > 1000) return 0
  return Math.round(value * 100)
})

const validationMessage = computed(() => {
  if (!amount.value.trim()) return '请输入转账金额'
  if (!amountCents.value) return '请输入 0.01 ～ 1000.00 之间的金额'
  return ''
})

const canSubmit = computed(() => !props.disabled && !props.submitting && !validationMessage.value)

const submit = () => {
  if (!canSubmit.value) return
  emit('confirm', amountCents.value, note.value.trim())
}
</script>

<template>
  <div class="transfer-backdrop" @click.self="emit('close')">
    <section class="transfer-dialog" role="dialog" aria-modal="true" aria-labelledby="transfer-title">
      <header class="transfer-dialog-header">
        <div>
          <span class="transfer-eyebrow">SIMULATED TRANSFER</span>
          <h2 id="transfer-title">给 {{ characterName || '角色' }} 转账</h2>
        </div>
        <button class="transfer-close" type="button" aria-label="关闭" @click="emit('close')">×</button>
      </header>

      <div class="transfer-dialog-body">
        <label class="transfer-amount-field">
          <span>转账金额</span>
          <div class="transfer-amount-input">
            <strong>¥</strong>
            <input
              v-model="amount"
              type="number"
              min="0.01"
              max="1000"
              step="0.01"
              inputmode="decimal"
              autofocus
              aria-label="转账金额"
              @keydown.enter="submit"
            />
          </div>
        </label>

        <label class="transfer-note-field">
          <span>备注 <small>可选</small></span>
          <input v-model="note" type="text" maxlength="80" placeholder="例如：请你喝奶茶" @keydown.enter="submit" />
        </label>

        <p v-if="validationMessage" class="transfer-validation">{{ validationMessage }}</p>
        <p class="transfer-tip">这是剧情演示金额，不会连接真实支付。{{ characterName || '角色' }}可能会收下，也可能退回。</p>
      </div>

      <footer class="transfer-dialog-footer">
        <button class="transfer-secondary" type="button" :disabled="submitting" @click="emit('close')">取消</button>
        <button class="transfer-primary" type="button" :disabled="!canSubmit" @click="submit">
          {{ submitting ? '处理中…' : '确认转账' }}
        </button>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.transfer-backdrop {
  position: fixed;
  z-index: 30;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(30, 31, 43, .3);
  backdrop-filter: blur(3px);
}

.transfer-dialog {
  width: min(410px, 100%);
  overflow: hidden;
  background: #fff;
  border: 1px solid #e8e7ef;
  border-radius: 20px;
  box-shadow: 0 24px 70px rgba(38, 36, 62, .2);
}

.transfer-dialog-header,
.transfer-dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.transfer-dialog-header {
  padding: 22px 24px 17px;
  border-bottom: 1px solid #f0f0f4;
}

.transfer-eyebrow {
  color: #a19da9;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: .12em;
}

.transfer-dialog h2 {
  margin: 7px 0 0;
  color: #343342;
  font-size: 18px;
  font-weight: 650;
}

.transfer-close {
  padding: 0 4px;
  color: #aaa8b2;
  background: transparent;
  border: 0;
  font-size: 25px;
  line-height: 1;
}

.transfer-dialog-body {
  padding: 24px;
}

.transfer-amount-field,
.transfer-note-field {
  display: block;
  color: #666575;
  font-size: 12px;
  font-weight: 600;
}

.transfer-amount-field > span,
.transfer-note-field > span {
  display: block;
  margin-bottom: 8px;
}

.transfer-note-field {
  margin-top: 18px;
}

.transfer-note-field small {
  color: #aaa8b2;
  font-size: 10px;
  font-weight: 400;
}

.transfer-amount-input,
.transfer-note-field input {
  width: 100%;
  border: 1px solid #e4e3eb;
  border-radius: 10px;
  background: #fafafd;
  outline: 0;
  transition: border-color .15s, box-shadow .15s;
}

.transfer-amount-input {
  display: flex;
  align-items: center;
  padding: 4px 14px;
}

.transfer-amount-input:focus-within,
.transfer-note-field input:focus {
  border-color: #b9b0f1;
  box-shadow: 0 0 0 3px rgba(118, 103, 232, .1);
}

.transfer-amount-input strong {
  color: #7569d7;
  font-size: 20px;
  font-weight: 650;
}

.transfer-amount-input input,
.transfer-note-field input {
  padding: 11px 12px;
  color: #343342;
  background: transparent;
  outline: 0;
  font: inherit;
}

.transfer-amount-input input {
  min-width: 0;
  flex: 1;
  border: 0;
  font-size: 25px;
  font-weight: 650;
}

.transfer-note-field input {
  font-size: 13px;
}

.transfer-validation {
  margin: 8px 0 0;
  color: #b45f72;
  font-size: 11px;
  font-weight: 400;
}

.transfer-tip {
  margin: 18px 0 0;
  color: #a2a0aa;
  font-size: 11px;
  line-height: 1.6;
}

.transfer-dialog-footer {
  justify-content: flex-end;
  gap: 9px;
  padding: 14px 24px 20px;
  background: #fafafd;
  border-top: 1px solid #f0f0f4;
}

.transfer-secondary,
.transfer-primary {
  padding: 9px 16px;
  border-radius: 9px;
  font-size: 12px;
}

.transfer-secondary {
  color: #777582;
  background: #fff;
  border: 1px solid #e2e1e9;
}

.transfer-primary {
  color: #fff;
  background: #7667e8;
  border: 1px solid #7667e8;
  box-shadow: 0 5px 12px rgba(118, 103, 232, .18);
}

.transfer-primary:disabled,
.transfer-secondary:disabled {
  cursor: not-allowed;
  opacity: .45;
}
</style>
