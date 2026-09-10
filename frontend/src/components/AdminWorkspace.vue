<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import CharacterStudio from './admin/CharacterStudio.vue'
import PromptLab from './admin/PromptLab.vue'
import ModelVoiceSettings from './admin/ModelVoiceSettings.vue'

const emit = defineEmits<{
  goChat: []
}>()

const activeTab = ref<'characters' | 'prompts' | 'model'>('characters')

const syncTabFromHash = () => {
  const hash = window.location.hash
  if (hash.includes('/admin/prompts')) {
    activeTab.value = 'prompts'
  } else if (hash.includes('/admin/model') || hash.includes('/admin/settings')) {
    activeTab.value = 'model'
  } else {
    activeTab.value = 'characters'
  }
}

const switchTab = (tab: 'characters' | 'prompts' | 'model') => {
  activeTab.value = tab
  if (tab === 'prompts') {
    window.location.hash = '#/admin/prompts'
  } else if (tab === 'model') {
    window.location.hash = '#/admin/model'
  } else {
    window.location.hash = '#/admin/characters'
  }
}

onMounted(() => {
  syncTabFromHash()
  window.addEventListener('hashchange', syncTabFromHash)
})

onUnmounted(() => {
  window.removeEventListener('hashchange', syncTabFromHash)
})
</script>

<template>
  <main class="admin-workspace-shell">
    <header class="admin-topbar">
      <div class="admin-brand">
        <span class="brand-dot" />
        <div>
          <strong>角色工作台</strong>
          <small>CHARACTER STUDIO</small>
        </div>
      </div>

      <nav class="admin-primary-nav" aria-label="后台主导航">
        <button
          class="nav-tab"
          type="button"
          @click="emit('goChat')"
        >
          <span>聊天体验</span>
        </button>
        <span class="nav-divider" />
        <button
          class="nav-tab"
          :class="{ active: activeTab === 'characters' }"
          type="button"
          @click="switchTab('characters')"
        >
          <span>角色管理</span>
        </button>
        <button
          class="nav-tab"
          :class="{ active: activeTab === 'prompts' }"
          type="button"
          @click="switchTab('prompts')"
        >
          <span>提示词编排</span>
        </button>
        <button
          class="nav-tab"
          :class="{ active: activeTab === 'model' }"
          type="button"
          @click="switchTab('model')"
        >
          <span>配置模型与语音</span>
        </button>
      </nav>

      <div class="topbar-right">
        <span class="mode-tag">本地管理模式</span>
      </div>
    </header>

    <div class="admin-view-content">
      <CharacterStudio v-if="activeTab === 'characters'" />
      <PromptLab v-else-if="activeTab === 'prompts'" />
      <ModelVoiceSettings v-else-if="activeTab === 'model'" />
    </div>
  </main>
</template>

<style scoped>
.admin-workspace-shell {
  min-height: 100vh;
  color: #272a38;
  background: #f7f7fa;
}

.admin-topbar {
  display: flex;
  align-items: center;
  gap: 28px;
  height: 64px;
  padding: 0 28px;
  background: #fff;
  border-bottom: 1px solid #e7e8ef;
  position: sticky;
  top: 0;
  z-index: 10;
}

.admin-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 200px;
}
.brand-dot {
  display: block;
  width: 11px;
  height: 11px;
  background: #7667e8;
  border-radius: 50%;
  box-shadow: 0 0 0 4px #e8e5ff;
}
.admin-brand strong {
  display: block;
  font-size: 15px;
  color: #222533;
}
.admin-brand small {
  display: block;
  margin-top: 2px;
  color: #9fa1ad;
  font-size: 9px;
  letter-spacing: .12em;
}

.admin-primary-nav {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 100%;
}
.nav-tab {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 40px;
  padding: 0 14px;
  color: #7b7e8e;
  background: transparent;
  border: 0;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all .15s;
}
.nav-tab:hover {
  background: #f4f4f8;
  color: #434657;
}
.nav-tab.active {
  color: #655bd0;
  background: #eeeaff;
  font-weight: 600;
}
.nav-divider {
  display: inline-block;
  width: 1px;
  height: 20px;
  background: #e5e5ec;
  margin: 0 4px;
}

.topbar-right {
  margin-left: auto;
  display: flex;
  align-items: center;
}
.mode-tag {
  padding: 4px 10px;
  background: #f0f1f6;
  color: #898b9a;
  border-radius: 6px;
  font-size: 11px;
}

.admin-view-content {
  min-height: calc(100vh - 64px);
}

@media (max-width: 760px) {
  .admin-topbar {
    padding: 0 12px;
    gap: 12px;
  }
  .admin-brand small, .mode-tag, .nav-divider {
    display: none;
  }
  .admin-brand {
    min-width: auto;
  }
  .nav-tab {
    padding: 0 8px;
    font-size: 11px;
  }
  .nav-tab span:last-child {
    display: none;
  }
}
</style>
