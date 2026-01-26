<template>
    <div class="hero-container">
        <h1 class="slogan">Lorem ipsum dolor sit amet consectetur adipiscing elit</h1>
        <button class="trial-btn">Free trial</button>
    </div>
</template>

<script lang="ts">
export default {
    name: 'FreeTrial'
}
</script>

<style scoped>
.hero-container {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 80vh;
    text-align: center;
    position: relative;
    background-image: url('../assets/free-trial.jpg');
    background-size: cover;
    background-position: center;
}

.slogan {
    font-size: 3rem;
    margin-bottom: 2rem;
    font-weight: 300;
    color: var(--black-main);
}

.trial-btn {
    padding: 1rem 2.5rem;
    border-radius: 2rem;
    background-color: var(--black-main);
    color: var(--white-main);
    font-size: 1.2rem;
    border: 1px solid var(--black-main);
    cursor: pointer;
    font-weight: 500;
    transition: all 0.3s ease;
    position: absolute;
    bottom: 2rem;
}
</style>