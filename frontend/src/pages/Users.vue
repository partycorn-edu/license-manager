<script setup>
import CrudPage from '../components/CrudPage.vue'

const roles = [{ value: 'admin', label: 'admin' }, { value: 'viewer', label: 'viewer' }]
const columns = [
  { key: 'username', label: 'Логин' },
  { key: 'role', label: 'Роль' },
  { key: 'is_active', label: 'Активен', format: (r) => (r.is_active ? 'да' : 'нет') },
]
// Пароль при изменении можно оставить пустым: бэкенд его тогда не меняет
const fields = [
  { key: 'username', label: 'Логин (только для нового)', required: true },
  { key: 'password', label: 'Пароль (мин. 6 символов)', skipEmptyOnEdit: true },
  { key: 'role', label: 'Роль', type: 'select', options: roles, default: 'viewer', required: true },
]
</script>
<template>
  <CrudPage title="Пользователи системы" endpoint="/auth/users" :columns="columns" :fields="fields" />
</template>
