<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const d = ref(null)
const error = ref('')
onMounted(async () => {
  try { d.value = await api('GET', '/api/dashboard') } catch (e) { error.value = e.message }
})
const when = (x) => (x.days_left < 0 ? `просрочена ${-x.days_left} дн. назад` : `осталось ${x.days_left} дн.`)
</script>

<template>
  <h2>Дашборд</h2>
  <div v-if="error" class="err">{{ error }}</div>
  <template v-if="d">
    <div class="cards">
      <div class="card stat"><b>{{ d.licenses_total }}</b><span>лицензий</span></div>
      <div class="card stat"><b>{{ d.seats_used }} / {{ d.seats_total }}</b><span>мест занято</span></div>
      <div class="card stat"><b>{{ d.seats_free }}</b><span>мест свободно</span></div>
      <div class="card stat"><b>{{ d.expiring.length }}</b><span>истекают за 30 дней</span></div>
      <div class="card stat"><b>{{ d.expired.length }}</b><span>просрочено</span></div>
    </div>
    <div class="card">
      Загрузка мест: {{ d.utilization_percent }}%
      <div class="bar"><div :style="{ width: d.utilization_percent + '%' }"></div></div>
    </div>
    <div class="card">
      <h3>Скоро истекают</h3>
      <p v-if="!d.expiring.length" class="muted">Нет</p>
      <ul><li v-for="x in d.expiring" :key="x.license_id">{{ x.software_name }}: {{ when(x) }} ({{ x.expiry_date }})</li></ul>
    </div>
    <div class="card">
      <h3>Просроченные</h3>
      <p v-if="!d.expired.length" class="muted">Нет</p>
      <ul><li v-for="x in d.expired" :key="x.license_id">{{ x.software_name }}: {{ when(x) }}</li></ul>
    </div>
    <div class="card">
      <h3>Перерасход мест</h3>
      <p v-if="!d.overused.length" class="muted">Нет</p>
      <ul><li v-for="x in d.overused" :key="x.license_id">{{ x.software_name }}: занято {{ x.used }} из {{ x.seats }}</li></ul>
    </div>
  </template>
</template>
