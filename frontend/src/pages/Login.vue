<script setup>
import { ref } from 'vue'
import { api, saveSession } from '../api'

const username = ref('')
const password = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    saveSession(await api('POST', '/auth/login', { username: username.value, password: password.value }))
  } catch (e) { error.value = e.message }
}
</script>

<template>
  <form class="card login" @submit.prevent="submit">
    <h2>Вход в систему</h2>
    <div v-if="error" class="err">{{ error }}</div>
    <label>Логин <input v-model="username" autocomplete="username" required /></label>
    <label>Пароль <input v-model="password" type="password" autocomplete="current-password" required /></label>
    <button class="btn" type="submit">Войти</button>
  </form>
</template>
