<script setup>
// Универсальная страница: таблица + форма добавления/редактирования.
// Всё настраивается через props, поэтому ПО, лицензии, сотрудники и назначения почти не содержат кода.
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { api, session } from '../api'

const props = defineProps({
  title: String,
  endpoint: String,
  columns: Array, // { key, label, format?(row) }
  fields: Array, // { key, label, type, options?, optionsFrom?:{url,value,label}, required, default, skipEmptyOnEdit }
  filters: { type: Array, default: () => [] }, // { key, label, options|optionsFrom }
  noEdit: Boolean,
  adminOnly: Boolean, // страница видна только admin
})

const rows = ref([])
const error = ref('')
const showForm = ref(false)
const editId = ref(null)
const form = reactive({})
const filterValues = reactive({})
const remote = reactive({}) // загруженные списки для select
const canWrite = computed(() => session.role === 'admin')

function emptyForm() {
  props.fields.forEach((f) => { form[f.key] = f.default ?? '' })
}

async function loadOptions() {
  for (const f of [...props.fields, ...props.filters]) {
    if (f.optionsFrom) remote[f.key] = await api('GET', f.optionsFrom.url)
  }
}

function optionsOf(f) {
  if (f.optionsFrom) {
    return (remote[f.key] || []).map((o) => ({
      value: o[f.optionsFrom.value],
      label: typeof f.optionsFrom.label === 'function' ? f.optionsFrom.label(o) : o[f.optionsFrom.label],
    }))
  }
  return f.options || []
}

async function load() {
  error.value = ''
  const qs = Object.entries(filterValues).filter(([, v]) => v !== '' && v != null)
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&')
  try {
    rows.value = await api('GET', props.endpoint + (qs ? `?${qs}` : ''))
  } catch (e) { error.value = e.message }
}

function startAdd() {
  editId.value = null
  emptyForm()
  showForm.value = true
}

function startEdit(row) {
  editId.value = row.id
  props.fields.forEach((f) => { form[f.key] = row[f.key] ?? f.default ?? '' })
  showForm.value = true
}

async function submit() {
  error.value = ''
  const body = {}
  props.fields.forEach((f) => {
    let v = form[f.key]
    if (f.type === 'number' || f.type === 'select-number') v = v === '' ? null : Number(v)
    if (f.type === 'date' && v === '') v = null
    if (editId.value && f.skipEmptyOnEdit && v === '') return // пустое поле при изменении не отправляем
    body[f.key] = v
  })
  try {
    if (editId.value) await api('PUT', `${props.endpoint}/${editId.value}`, body)
    else await api('POST', props.endpoint, body)
    showForm.value = false
    await load()
  } catch (e) { error.value = e.message }
}

async function remove(row) {
  if (!confirm('Удалить запись?')) return
  try {
    await api('DELETE', `${props.endpoint}/${row.id}`)
    await load()
  } catch (e) { error.value = e.message }
}

function cell(row, c) {
  return c.format ? c.format(row) : (row[c.key] ?? '')
}

watch(filterValues, load)
onMounted(async () => { emptyForm(); await loadOptions(); await load() })
</script>

<template>
  <h2>{{ title }}</h2>
  <div v-if="error" class="err">{{ error }}</div>

  <div class="row">
    <label v-for="f in filters" :key="f.key">{{ f.label }}
      <select v-model="filterValues[f.key]">
        <option value="">Все</option>
        <option v-for="o in optionsOf(f)" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
    </label>
    <button v-if="canWrite" class="btn" @click="startAdd">Добавить</button>
  </div>

  <form v-if="showForm" class="card" @submit.prevent="submit">
    <div class="row">
      <label v-for="f in fields" :key="f.key">{{ f.label }}
        <select v-if="f.type === 'select' || f.type === 'select-number'" v-model="form[f.key]" :required="f.required">
          <option value="" disabled>Выберите</option>
          <option v-for="o in optionsOf(f)" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
        <input v-else v-model="form[f.key]" :type="f.type || 'text'" :required="f.required" :min="f.type === 'number' ? 0 : undefined" />
      </label>
    </div>
    <button class="btn" type="submit">Сохранить</button>
    <button class="btn gray" type="button" style="margin-left: 8px" @click="showForm = false">Отмена</button>
  </form>

  <div class="table-wrap">
    <table>
      <thead>
        <tr><th v-for="c in columns" :key="c.key">{{ c.label }}</th><th v-if="canWrite"></th></tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id">
          <td v-for="c in columns" :key="c.key">
            <span v-if="c.badge" :class="['badge', r[c.key]]">{{ cell(r, c) }}</span>
            <template v-else>{{ cell(r, c) }}</template>
          </td>
          <td v-if="canWrite" style="white-space: nowrap">
            <button v-if="!noEdit" class="btn small" @click="startEdit(r)">Изменить</button>
            <button class="btn small red" style="margin-left: 4px" @click="remove(r)">Удалить</button>
          </td>
        </tr>
        <tr v-if="!rows.length"><td :colspan="columns.length + 1" class="muted">Записей нет</td></tr>
      </tbody>
    </table>
  </div>
  <p v-if="!canWrite" class="muted">Режим просмотра: изменять данные может только администратор.</p>
</template>
