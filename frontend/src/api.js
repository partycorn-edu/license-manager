// Тонкая обёртка над fetch: подставляет токен и разбирает ошибки
import { reactive } from 'vue'

export const session = reactive({
  token: localStorage.getItem('token') || '',
  username: localStorage.getItem('username') || '',
  role: localStorage.getItem('role') || '',
})

export function saveSession(data) {
  session.token = data.access_token
  session.username = data.username
  session.role = data.role
  localStorage.setItem('token', data.access_token)
  localStorage.setItem('username', data.username)
  localStorage.setItem('role', data.role)
}

export function logout() {
  session.token = session.username = session.role = ''
  localStorage.clear()
}

export async function api(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(session.token ? { Authorization: `Bearer ${session.token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (res.status === 401 && session.token) {
    logout() // токен просрочен, возвращаем на экран входа
  }
  if (!res.ok) {
    let msg = `Ошибка ${res.status}`
    try {
      const data = await res.json()
      if (typeof data.detail === 'string') msg = data.detail
      else if (Array.isArray(data.detail)) msg = data.detail.map((d) => d.msg).join('; ')
    } catch { /* тела нет */ }
    throw new Error(msg)
  }
  return res.status === 204 ? null : res.json()
}
