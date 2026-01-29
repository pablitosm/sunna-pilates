<template>
    <div class="app-access-container">
        <h2 class="title">Acceso App</h2>
        <div class="buttons-group">
            <a href="#" class="store-link">
                <img src="https://placehold.co/150x50?text=Google+Play" alt="Google Play" class="store-img" />
            </a>
            <a href="#" class="store-link">
                <img src="https://placehold.co/150x50?text=App+Store" alt="App Store" class="store-img" />
            </a>
        </div>
    </div>
</template>

<script lang="ts">
export default {
    name: 'AppAccess'
}
</script>

<style scoped>
.app-access-container {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 60px 30px;
    gap: 40px;
}

.title {
    font-size: 2rem;
    font-weight: 300;
    color: var(--black-main);
    margin: 0;
}

.buttons-group {
    display: flex;
    gap: 20px;
}

.store-img {
    height: 50px;
    width: auto;
    border-radius: 10px;
    border: 1px solid var(--black-main);
    transition: transform 0.2s ease;
}

@media (max-width: 768px) {
    .app-access-container {
        flex-direction: column;
        text-align: center;
        gap: 20px;
    }
}
</style>
