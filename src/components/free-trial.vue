<template>
    <div class="image-container">
        <h2 class="slogan">Tu cuerpo. Tu ritmo. Tu entrenamiento.</h2>
        <button class="trial-btn">Comienza tu prueba gratuita</button>
    </div>
</template>

<script lang="ts">
export default {
    name: 'FreeTrial'
}
</script>

<style scoped>
.image-container {
    margin: 15px 15px 0 15px;
    /*border-radius: 20px;*/
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 80vh;
    text-align: center;
    position: relative;
    background-image: url('../assets/images/home-sunna.jpg');
    background-size: cover;
    background-position: center;
}

.slogan {
    font-style: italic;
    font-weight: bold;
    font-size: 3rem;
    font-weight: 500;
    margin-bottom: 2rem;
    color: var(--white-main);
}

.trial-btn {
    padding: 1rem 2.5rem;
    border-radius: 2rem;
    background-color: var(--white-main);
    color: var(--black-main);
    font-size: 1rem;
    border: 1px solid var(--white-main);
    cursor: pointer;
    font-weight: 500;
    transition: all 0.3s ease;
    position: absolute;
    bottom: 12rem;
}

</style>