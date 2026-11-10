<script setup>
import { computed, ref } from 'vue'
import { session, logout } from './api'
import Login from './pages/Login.vue'
import Dashboard from './pages/Dashboard.vue'
import Software from './pages/Software.vue'
import Licenses from './pages/Licenses.vue'
import Employees from './pages/Employees.vue'
import Assignments from './pages/Assignments.vue'
import Notifications from './pages/Notifications.vue'
import Users from './pages/Users.vue'

const pages = [
  { id: 'dashboard', title: 'Дашборд', comp: Dashboard },
  { id: 'software', title: 'ПО', comp: Software },
  { id: 'licenses', title: 'Лицензии', comp: Licenses },
  { id: 'employees', title: 'Сотрудники', comp: Employees },
  { id: 'assignments', title: 'Назначения', comp: Assignments },
  { id: 'notifications', title: 'Уведомления', comp: Notifications },
  { id: 'users', title: 'Пользователи', comp: Users, adminOnly: true },
]
const current = ref('dashboard')
const visible = computed(() => pages.filter((p) => !p.adminOnly || session.role === 'admin'))
const comp = computed(() => pages.find((p) => p.id === current.value).comp)
</script>

<template>
  <Login v-if="!session.token" />
  <div v-else class="layout">
    <header class="top">
      <strong>Учёт лицензий</strong>
      <nav>
        <button v-for="p in visible" :key="p.id" :class="{ active: current === p.id }" @click="current = p.id">
          {{ p.title }}
        </button>
      </nav>
      <span class="user">{{ session.username }} ({{ session.role }})
        <button class="link" @click="logout">Выйти</button></span>
    </header>
    <main><component :is="comp" :key="current" /></main>
  </div>
</template>
