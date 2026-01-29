<template>
  <div class="habits-container">
    <div class="image-column">
      <img src="https://placehold.co/800x1200" alt="Clases y hábitos" class="image" />
    </div>
    <div class="text-column">
      <h2 class="title">Clases/hábitos</h2>
      <div class="habits-list">
        <span class="habit-item">Fuerza</span>
        <span class="habit-item">Flexibilidad</span>
        <span class="habit-item">Constancia</span>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
export default {
  name: 'ClassHabits'
}
</script>

<style scoped>
.habits-container {
  display: flex;
  flex-direction: row;
  padding: 0 30px 30px 30px;
  align-items: center;
  max-height: 80vh;
}

.image-column {
  flex: 1;
  max-height: 80vh;
  margin-right: 30px;
}

.image {
  border-radius: 10px;
  box-sizing: border-box;
  border: 1px solid var(--black-main);
  width: 100%;
  max-height: 80vh;
  object-fit: cover;
}

.text-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
}

.title {
  font-size: 2.2rem;
  font-weight: 300;
  margin-bottom: 30px;
  color: var(--black-main);
}

.habits-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
  align-items: center;
}

.habit-item {
  font-size: 1.2rem;
  line-height: 1.5;
  font-weight: 300;
  color: var(--black-main);
}

@media (max-width: 768px) {
  .habits-container {
    flex-direction: column;
    max-height: none;
    margin-top: 30px;
  }

  .image-column {
    margin-right: 0;
    margin-bottom: 30px;
    width: 100%;
    max-height: none;
  }
}
</style>
