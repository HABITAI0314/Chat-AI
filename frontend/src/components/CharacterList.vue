<script setup lang="ts">
import type { Character } from '../types/chat'

defineProps<{
  characters: Character[]
  selectedId?: number
}>()

const emit = defineEmits<{
  select: [character: Character]
  'open-admin': []
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

    <button class="admin-link" type="button" @click="emit('open-admin')">
      <span>✦</span>
      <span>打开角色后台</span>
    </button>

    <div class="virtual-note">
      <span>✦</span>
      <p>这里的角色都是虚构设定，用来体验不同的人设、情绪和剧情。</p>
    </div>
  </aside>
</template>
