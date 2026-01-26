<template>
    <nav class="menu-bar">
        <div class="left-section">
            <button class="join-btn">Join now</button>
            <span class="login-text">Login</span>
        </div>

        <div class="center-section">
            <span class="brand">SUNNA PILATES</span>
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
    font-size: 1.5rem;
    font-weight: bold;
    text-transform: uppercase;
}

.join-btn {
    padding: 0.6rem 1.5rem;
    border-radius: 2rem;
    background-color: var(--black-main);
    color: var(--white-main);
    font-size: 0.9rem;
    border: 1px solid var(--black-main);
    cursor: pointer;
    font-weight: 500;
    transition: all 0.3s ease;
    letter-spacing: 0.5px;
}

.join-btn:hover {
    background-color: transparent;
    color: var(--black-main);
}

.login-text, .about-text {
    cursor: pointer;
    font-size: 0.9rem;
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
    transition: width 0.3s ease;
}

.login-text:hover::after, .about-text:hover::after {
    width: 100%;
}
</style>
