<template>
    <div class="image-container">
        <h2 class="slogan">Tu cuerpo. Tu ritmo. Tu entrenamiento.</h2>
        <!--<button class="trial-btn">Comienza tu prueba gratuita</button>-->
    </div>
</template>

<script lang="ts">
export default {
    name: 'FreeTrial'
}
</script>

<style scoped>
.image-container {
    margin: 30px 30px 0 30px;
    border-radius: 10px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 80vh;
    text-align: center;
    position: relative;
    border: 1px solid var(--black-main);
    background-image: url('https://placehold.co/1920x1080');
    background-size: cover;
    background-position: center;
}

.slogan {
    font-style: italic;
    font-weight: bold;
    font-size: 3rem;
    font-weight: 300;
    margin-bottom: 2rem;
    color: var(--white-main);
}

.trial-btn {
    padding: 1rem 2.5rem;
    border-radius: 2rem;
    background-color: var(--white-main);
    color: var(--black-main);
    font-size: 1rem;
    border: 1px solid var(--black-main);
    cursor: pointer;
    font-weight: 500;
    position: absolute;
    bottom: 12rem;
}

</style>
