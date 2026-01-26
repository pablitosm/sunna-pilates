<template>
    <nav class="menu-bar">
        <div class="left-section">
            <button class="join-btn">Únete ahora</button>
            </div>

        <div class="center-section">
            <a href="/" class="brand">
                <img src="../assets/images/logo-navbar.png" alt="SUNNA Pilates" class="logo" />
            </a>
        </div>

        <div class="right-section">
            <span class="about-text">Nuestro estudio</span>
            <span class="about-text">Quienes somos</span>
            <span class="about-text">Contacto</span>
        </div>
    </nav>
</template>

<script lang="ts">
export default {
    name: 'MenuBar'
}
</script>

<style scoped>
.menu-bar {
    border-radius: 0 0 15px 15px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 2rem;
    background-color: var(--white-main);
    color: var(--black-main);
    position: relative;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
}

.left-section {
    display: flex;
    align-items: center;
    gap: 1.5rem;
}

.center-section {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
}

.right-section {
    display: flex;
    align-items: center;
    gap: 1.5rem;
}

.brand {
    text-decoration: none;
    color: var(--black-main);
    display: flex;
}

.logo {
    height: 40px;
    width: auto;
}

.join-btn {
    padding: 0.6rem 1.5rem;
    border-radius: 2rem;
    background-color: var(--corporative-color);
    color: var(--white-main);
    font-size: 1rem;
    border: 1px solid var(--corporative-color);
    cursor: pointer;
    letter-spacing: 0.5px;
    transition: all 0.3s ease;
}

.join-btn:hover {
    background-color: transparent;
    color: var(--black-main);
}

.login-text, .about-text {
    cursor: pointer;
    font-size: 1rem;
    font-weight: 300;
    position: relative;
    padding-bottom: 2px;
}

.login-text::after, .about-text::after {
    content: '';
    position: absolute;
    width: 0;
    height: 1px;
    bottom: 0;
    left: 0;
    background-color: var(--black-main);
}

.login-text:hover::after, .about-text:hover::after {
    width: 100%;
}
</style>
