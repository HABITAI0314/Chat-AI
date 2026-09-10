<script setup lang="ts">
import { computed } from 'vue'
import type { Message, TransferMetadata, TransferStatus } from '../types/chat'

const props = defineProps<{
  message: Message
}>()

const transfer = computed(() => (props.message.metadata || {}) as Partial<TransferMetadata>)

const amountLabel = computed(() => {
  const cents = Number(transfer.value.amount_cents)
  if (!Number.isFinite(cents) || cents < 0) return '¥0.00'
  return `¥${(cents / 100).toFixed(2)}`
})

const status = computed<TransferStatus>(() => {
  const value = transfer.value.status
  return value === 'accepted' || value === 'returned' || value === 'failed' || value === 'pending'
    ? value
    : 'pending'
})

const statusLabel = computed(() => ({
  pending: '处理中',
  accepted: '对方已收款',
  returned: '已退回',
  failed: '转账失败',
})[status.value])

const statusClass = computed(() => `is-${status.value}`)
</script>

<template>
  <div class="transfer-card" :class="[message.role, statusClass]">
    <div class="transfer-card-main">
      <div class="transfer-icon">↗</div>
      <div class="transfer-card-copy">
        <strong>模拟转账</strong>
        <span>{{ statusLabel }}</span>
      </div>
      <strong class="transfer-card-amount">{{ amountLabel }}</strong>
    </div>
    <p v-if="transfer.note" class="transfer-card-note">{{ transfer.note }}</p>
    <div class="transfer-card-footer">
      <span>虚拟剧情金额</span>
      <span>{{ status === 'returned' ? '金额已退回' : status === 'accepted' ? '已完成' : '请稍候' }}</span>
    </div>
  </div>
</template>

<style scoped>
.transfer-card {
  width: min(285px, 100%);
  padding: 14px 15px 11px;
  color: #fff;
  background: linear-gradient(135deg, #7b70e6, #6659cf);
  border-radius: 5px 15px 15px 15px;
  box-shadow: 0 7px 17px rgba(97, 84, 200, .16);
}

.transfer-card.is-returned {
  background: linear-gradient(135deg, #8c83b9, #716a9e);
}

.transfer-card.is-failed {
  background: linear-gradient(135deg, #ad7b88, #956574);
}

.transfer-card-main {
  display: flex;
  align-items: center;
  gap: 10px;
}

.transfer-icon {
  display: grid;
  width: 35px;
  height: 35px;
  place-items: center;
  color: #7569d7;
  background: #fff;
  border-radius: 50%;
  font-size: 20px;
  font-weight: 700;
}

.transfer-card-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 3px;
}

.transfer-card-copy strong {
  font-size: 13px;
  font-weight: 650;
}

.transfer-card-copy span,
.transfer-card-footer {
  color: rgba(255, 255, 255, .72);
  font-size: 10px;
}

.transfer-card-amount {
  font-size: 17px;
  font-weight: 650;
  white-space: nowrap;
}

.transfer-card-note {
  overflow: hidden;
  margin: 13px 0 9px 45px;
  color: rgba(255, 255, 255, .88);
  font-size: 11px;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.transfer-card-footer {
  display: flex;
  justify-content: space-between;
  padding-top: 9px;
  margin-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, .2);
}
</style>
