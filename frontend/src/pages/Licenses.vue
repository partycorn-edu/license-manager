<script setup>
import CrudPage from '../components/CrudPage.vue'

const types = [
  { value: 'perpetual', label: 'Бессрочная' },
  { value: 'subscription', label: 'Подписка' },
  { value: 'per_user', label: 'На пользователя' },
  { value: 'floating', label: 'Плавающая' },
]
const statuses = [
  { value: 'ok', label: 'В порядке' },
  { value: 'expiring', label: 'Скоро истекает' },
  { value: 'expired', label: 'Просрочена' },
  { value: 'overused', label: 'Перерасход' },
]
const typeName = (r) => types.find((t) => t.value === r.license_type)?.label
const statusName = (r) => statuses.find((s) => s.value === r.status)?.label
const software = { url: '/api/software', value: 'id', label: 'name' }

const columns = [
  { key: 'software_name', label: 'ПО' },
  { key: 'license_type', label: 'Тип', format: typeName },
  { key: 'used', label: 'Места', format: (r) => `${r.used} / ${r.seats}` },
  { key: 'expiry_date', label: 'Окончание', format: (r) => r.expiry_date || 'бессрочно' },
  { key: 'cost', label: 'Стоимость', format: (r) => Number(r.cost).toLocaleString('ru-RU') + ' ₽' },
  { key: 'contract', label: 'Договор' },
  { key: 'license_key_masked', label: 'Ключ' },
  { key: 'status', label: 'Статус', format: statusName, badge: true },
]
const fields = [
  { key: 'software_id', label: 'ПО', type: 'select-number', optionsFrom: software, required: true },
  { key: 'license_type', label: 'Тип', type: 'select', options: types, required: true, default: 'subscription' },
  { key: 'seats', label: 'Число мест', type: 'number', required: true, default: 1 },
  { key: 'purchase_date', label: 'Дата покупки', type: 'date', required: true },
  { key: 'expiry_date', label: 'Дата окончания', type: 'date' },
  { key: 'cost', label: 'Стоимость, ₽', type: 'number', default: 0 },
  { key: 'contract', label: 'Договор или заметка' },
  { key: 'license_key', label: 'Лицензионный ключ (при изменении можно не заполнять)' },
]
const filters = [
  { key: 'software_id', label: 'ПО', optionsFrom: software },
  { key: 'license_type', label: 'Тип', options: types },
  { key: 'status', label: 'Статус', options: statuses },
]
</script>
<template><CrudPage title="Лицензии" endpoint="/api/licenses" :columns="columns" :fields="fields" :filters="filters" /></template>
