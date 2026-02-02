<template>
    <div class="image-container">
        <div class="content-wrapper">
            <h2 class="slogan">Pilates flexible. Sin horarios fijos.</h2>
            <p class="description">Un sistema semi-autónomo que se adapta a tu agenda. Reserva tu hueco, ven cuando quieras y entrena a tu propio ritmo con nuestra supervisión.</p>
            <button class="trial-btn">Comienza tu prueba gratuita</button>
        </div>
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
    justify-content: flex-start;
    align-items: flex-start;
    height: 80vh;
    position: relative;
    border: 1px solid var(--black-main);
    background-image: url('../assets/images/free-trial/home-sunna-1.jpg');
    background-size: cover;
    background-position: center;
    padding: 0 60px;
    padding: 100px 60px;
}

.content-wrapper {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
    max-width: 50%;
}

.slogan {
    font-style: italic;
    font-weight: bold;
    font-size: 3rem;
    font-weight: 300;
    color: var(--black-main);
    text-align: left;
    margin: 0;
}

.description {
    font-size: 1.2rem;
    color: var(--black-main);
    font-weight: 300;
    text-align: left;
    margin: 0;
}

.trial-btn {
    padding: 1.5rem 3rem;
    border-radius: 2rem;
    background-color: var(--white-main);
    color: var(--black-main);
    font-size: 1.2rem;
    border: none;
    cursor: pointer;
    font-weight: 500;
    transition: transform 0.3s ease;
}

</style>
