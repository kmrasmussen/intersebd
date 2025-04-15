import { createRouter, createWebHistory } from 'vue-router'
import InterceptRequestMessages from '../views/InterceptRequestMessages.vue'
import Home from '../views/Home.vue'
import { useAuth } from '../auth'

const routes = [
  {
    path: '/',
    name: 'home',
    component: Home
  },
  {
    path: '/intercept/:interceptKey/unique_request_messages',
    name: 'unique-request-messages',
    component: InterceptRequestMessages,
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router