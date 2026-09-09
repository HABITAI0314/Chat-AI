export interface Character {
  id: number
  code: string
  name: string
  description: string
  avatar_url: string
  is_virtual: boolean
}

export type MessageType = 'text' | 'image' | 'audio'

export interface Message {
  id: number
  role: 'user' | 'assistant'
  message_type: MessageType
  content: string | null
  image_url?: string | null
  audio_url?: string | null
  audio_duration_ms?: number | null
  transcript?: string | null
  metadata?: Record<string, unknown>
  created_at: string
  delay_ms?: number
}

export interface Conversation {
  id: number
  user_id: string
  character: Character
  relationship: Record<string, number>
  emotion: Record<string, unknown>
  scene: Record<string, unknown>
}

export interface ChatResponse {
  user_message: Message
  assistant_messages: Message[]
  state: {
    relationship: Record<string, number>
    emotion: Record<string, unknown>
    scene: Record<string, unknown>
  }
}

export interface ChatMemory {
  id: number
  memory_type: 'preference' | 'experience' | 'important_event' | 'boundary'
  content: string
  importance: number
  created_at: string
}
