<script setup>
import CrudPage from '../components/CrudPage.vue'

const licenseOpt = {
  url: '/api/licenses', value: 'id',
  label: (l) => `${l.software_name} (занято ${l.used} из ${l.seats})`,
}
const employeeOpt = { url: '/api/employees', value: 'id', label: 'full_name' }

const columns = [
  { key: 'software_name', label: 'ПО' },
  { key: 'employee_name', label: 'Сотрудник' },
  { key: 'assigned_at', label: 'Выдано', format: (r) => (r.assigned_at || '').replace('T', ' ').slice(0, 16) },
]
const fields = [
  { key: 'license_id', label: 'Лицензия', type: 'select-number', optionsFrom: licenseOpt, required: true },
  { key: 'employee_id', label: 'Сотрудник', type: 'select-number', optionsFrom: employeeOpt, required: true },
]
const filters = [
  { key: 'license_id', label: 'Лицензия', optionsFrom: licenseOpt },
  { key: 'employee_id', label: 'Сотрудник', optionsFrom: employeeOpt },
]
</script>
<template>
  <CrudPage title="Назначения лицензий" endpoint="/api/assignments" :columns="columns" :fields="fields" :filters="filters" no-edit />
</template>
