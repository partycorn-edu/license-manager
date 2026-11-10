<script setup>
import { computed, onMounted, ref } from 'vue'
import { api, session } from '../api'

const rows = ref([])
const error = ref('')
const canWrite = computed(() => session.role === 'admin')
const kinds = { expiring: 'Истекает', expired: 'Просрочена', seats_full: 'Нет мест', overuse: 'Перерасход' }

async function load() {
  try { rows.value = await api('GET', '/api/notifications') } catch (e) { error.value = e.message }
}
async function read(id) {
  await api('POST', `/api/notifications/${id}/read`)
  await load()
}
async function readAll() {
  await api('POST', '/api/notifications/read-all')
  await load()
}
onMounted(load)
</script>

<template>
  <h2>Уведомления</h2>
  <div v-if="error" class="err">{{ error }}</div>
  <div class="row"><button v-if="canWrite" class="btn gray" @click="readAll">Отметить все прочитанными</button></div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Тип</th><th>Сообщение</th><th>Создано</th><th v-if="canWrite"></th></tr></thead>
      <tbody>
        <tr v-for="n in rows" :key="n.id" :style="{ opacity: n.is_read ? 0.5 : 1 }">
          <td><span class="badge">{{ kinds[n.kind] || n.kind }}</span></td>
          <td>{{ n.message }}</td>
          <td>{{ (n.created_at || '').replace('T', ' ').slice(0, 16) }}</td>
          <td v-if="canWrite"><button v-if="!n.is_read" class="btn small" @click="read(n.id)">Прочитано</button></td>
        </tr>
        <tr v-if="!rows.length"><td colspan="4" class="muted">Уведомлений нет</td></tr>
      </tbody>
    </table>
  </div>
</template>
