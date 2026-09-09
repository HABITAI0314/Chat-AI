import type { Character, ChatMemory, ChatResponse, Conversation, Message } from '../types/chat'

const json = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || '请求失败：' + response.status)
  }
  return response.json() as Promise<T>
}

export const api = {
  async characters(): Promise<Character[]> {
    return json<Character[]>(await fetch('/api/characters'))
  },

  async openConversation(userId: string, characterId: number): Promise<Conversation> {
    return json<Conversation>(
      await fetch('/api/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, character_id: characterId }),
      }),
    )
  },

  async history(conversationId: number, userId: string): Promise<{
    conversation: Conversation
    messages: Message[]
  }> {
    const url = '/api/conversations/' + conversationId + '/messages?user_id=' + encodeURIComponent(userId)
    return json(await fetch(url))
  },

  async send(conversationId: number, userId: string, content: string): Promise<ChatResponse> {
    const url = '/api/conversations/' + conversationId + '/messages'
    return json<ChatResponse>(
      await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, content }),
      }),
    )
  },

  async resetConversation(conversationId: number, userId: string): Promise<Conversation> {
    const url = '/api/conversations/' + conversationId + '/messages?user_id=' + encodeURIComponent(userId)
    return json<Conversation>(await fetch(url, { method: 'DELETE' }))
  },

  async memories(conversationId: number, userId: string): Promise<ChatMemory[]> {
    const url = '/api/conversations/' + conversationId + '/memories?user_id=' + encodeURIComponent(userId)
    return json<ChatMemory[]>(await fetch(url))
  },

  async deleteMemory(conversationId: number, memoryId: number, userId: string): Promise<void> {
    const url = '/api/conversations/' + conversationId + '/memories/' + memoryId + '?user_id=' + encodeURIComponent(userId)
    const response = await fetch(url, { method: 'DELETE' })
    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      throw new Error(body.detail || '删除记忆失败：' + response.status)
    }
  },
}
