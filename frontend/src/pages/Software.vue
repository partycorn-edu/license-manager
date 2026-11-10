<script setup>
import CrudPage from '../components/CrudPage.vue'
const columns = [
  { key: 'name', label: 'Название' },
  { key: 'vendor', label: 'Вендор' },
  { key: 'category', label: 'Категория' },
]
const fields = [
  { key: 'name', label: 'Название', required: true },
  { key: 'vendor', label: 'Вендор' },
  { key: 'category', label: 'Категория' },
]
</script>
<template><CrudPage title="Программное обеспечение" endpoint="/api/software" :columns="columns" :fields="fields" /></template>
