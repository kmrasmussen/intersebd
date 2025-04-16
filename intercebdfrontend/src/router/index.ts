import { createRouter, createWebHistory } from 'vue-router'
import InterceptRequestMessages from '../views/InterceptRequestMessages.vue'
import Home from '../views/Home.vue'
import CompletionPairs from '../views/CompletionPairs.vue'
import GuestRedirect from '../views/GuestRedirect.vue';

const routes = [
  {
    path: '/',
    name: 'home',
    component: Home
  },
  {
    path: '/guest',
    name: 'guest-redirect',
    component: GuestRedirect
  },
  {
    path: '/intercept/:interceptKey/unique_request_messages',
    name: 'unique-request-messages',
    component: InterceptRequestMessages,
    props: true
  },
  {
    path: '/completion-pairs/view/:viewingId',
    name: 'completion-pairs-view',
    component: CompletionPairs
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router