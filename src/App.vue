<script setup lang="ts">
  import TopMenu from './components/nav-bar.vue'
  import FreeTrial from './components/free-trial.vue'
  import FooterBar from './components/footer-bar.vue'
  import JoinNow from './components/join-now.vue'
  import ClassHabits from './components/habits-classes.vue'
  import SunnaModalities from './components/sunna-modalities.vue'
  import AppAccess from './components/app-access.vue'
</script>

<template>
  <TopMenu />
    <FreeTrial />
    <JoinNow />
    <SunnaModalities />
    <ClassHabits />
    <AppAccess />
  <FooterBar />
</template>

<style>
@import './assets/styles/variables.css';
</style>

<style scoped></style>
