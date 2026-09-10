<script setup lang="ts">
import type { Character } from '../types/chat'

defineProps<{
  characters: Character[]
  selectedId?: number
}>()

const emit = defineEmits<{
  select: [character: Character]
  'open-admin': [target?: 'characters' | 'prompts' | 'model']
}>()
</script>

<template>
  <aside class="character-list">
    <div class="brand-lockup">
      <span class="brand-dot" />
      <div>
        <strong>角色聊天</strong>
        <small>1v1 fictional chat</small>
      </div>
    </div>

    <div class="list-heading">
      <span>选择角色</span>
      <span class="count">{{ characters.length }}</span>
    </div>

    <div class="character-items-container">
      <button
        v-for="character in characters"
        :key="character.id"
        class="character-card"
        :class="{ active: character.id === selectedId }"
        type="button"
        @click="emit('select', character)"
      >
        <img :src="character.avatar_url" :alt="character.name" />
        <span class="character-copy">
          <strong>{{ character.name }}</strong>
          <small>{{ character.description }}</small>
        </span>
        <span class="chevron">›</span>
      </button>
    </div>

    <div class="admin-quick-entries">
      <button class="admin-entry-btn model-highlight-btn" type="button" @click="emit('open-admin', 'model')">
        <span class="btn-main-info">
          <span class="btn-dot" />
          <span class="btn-title">配置模型与语音</span>
        </span>
        <span class="btn-arrow">›</span>
      </button>

      <button class="admin-entry-btn studio-btn" type="button" @click="emit('open-admin', 'characters')">
        <span class="btn-main-info">
          <span class="btn-title">角色管理工坊</span>
        </span>
        <span class="btn-arrow">›</span>
      </button>

      <div class="admin-sub-links">
        <button type="button" @click="emit('open-admin', 'prompts')">
          提示词编排 (Prompt Lab)
        </button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.character-items-container {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 12px;
}

.admin-quick-entries {
  margin: 8px 8px 12px;
  padding: 10px;
  background: #e9e8f7;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.admin-entry-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 12px;
  cursor: pointer;
  transition: all .16s ease;
  text-align: left;
}

.btn-main-info {
  display: flex;
  align-items: center;
  gap: 7px;
}

.btn-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #6a5ce8;
  box-shadow: 0 0 0 2px rgba(106, 92, 232, 0.2);
}

.admin-entry-btn.model-highlight-btn {
  background: #fff;
  border: 1.5px solid #6f62e8;
  color: #5547cb;
  font-weight: 650;
  box-shadow: 0 2px 6px rgba(111, 98, 232, 0.12);
}
.admin-entry-btn.model-highlight-btn:hover {
  background: #f5f3ff;
  border-color: #5949d6;
  color: #4333bd;
  box-shadow: 0 3px 8px rgba(111, 98, 232, 0.2);
  transform: translateY(-1px);
}

.admin-entry-btn.studio-btn {
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid #dcdbe9;
  color: #56596b;
  font-weight: 550;
}
.admin-entry-btn.studio-btn:hover {
  background: #fff;
  color: #383a48;
}

.btn-arrow {
  font-size: 13px;
  color: #9896b8;
}

.admin-sub-links {
  display: flex;
  align-items: center;
  justify-content: center;
  padding-top: 2px;
}
.admin-sub-links button {
  padding: 3px 8px;
  color: #726db0;
  background: transparent;
  border: 0;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  transition: all .15s;
}
.admin-sub-links button:hover {
  color: #4739ba;
  background: rgba(255, 255, 255, 0.6);
}
</style>
