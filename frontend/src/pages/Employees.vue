<script setup>
import CrudPage from '../components/CrudPage.vue'
const columns = [
  { key: 'full_name', label: 'ФИО' },
  { key: 'department', label: 'Отдел' },
  { key: 'email', label: 'Email' },
]
const fields = [
  { key: 'full_name', label: 'ФИО', required: true },
  { key: 'department', label: 'Отдел' },
  { key: 'email', label: 'Email', type: 'email', required: true },
]
</script>
<template><CrudPage title="Сотрудники" endpoint="/api/employees" :columns="columns" :fields="fields" /></template>
