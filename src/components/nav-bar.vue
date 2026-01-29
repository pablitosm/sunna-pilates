<template>
    <nav class="menu-bar">
        <button class="hamburger-btn" @click="toggleMenu" aria-label="Menú">
            <span class="bar"></span>
            <span class="bar"></span>
            <span class="bar"></span>
        </button>

        <div class="logo-section">
            <a href="/" class="brand">
                <!-- SUNNA PILATES -->
                <img src="../assets/images/nav-bar/logo-navbar.png" alt="SUNNA Pilates" class="logo" />
            </a>
        </div>

        <div class="menu-items" :class="{ 'open': isMenuOpen }">
            <span class="about-text">Quienes somos</span>
            <span class="about-text">Contacto</span>
            <span class="about-text">Únete ahora</span>
        <!-- <button class="join-btn">Únete ahora</button> -->
        </div>
    </nav>
</template>

<script lang="ts">
export default {
    name: 'MenuBar',
    data() {
        return {
            isMenuOpen: false
        }
    },
    methods: {
        toggleMenu() {
            this.isMenuOpen = !this.isMenuOpen;
        }
    }
}
</script>

<style scoped>
.menu-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 15px 20px 15px;
    background-color: var(--white-main);
    color: var(--black-main);
    position: relative;
    border-bottom: 1px solid var(--black-main);
    z-index: 100;
}

.hamburger-btn {
    display: none;
    flex-direction: column;
    justify-content: space-between;
    width: 30px;
    height: 21px;
    background: transparent;
    border: none;
    cursor: pointer;
    padding: 0;
    z-index: 10;
}

.bar {
    width: 100%;
    height: 3px;
    background-color: var(--black-main);
    border-radius: 10px;
    transition: all 0.3s linear;
}

.logo-section {
    display: flex;
    align-items: center;
    gap: 1.5rem;
}

.menu-items {
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

.login-text,
.about-text {
    cursor: pointer;
    font-size: 1rem;
    font-weight: 300;
    position: relative;
    padding-bottom: 2px;
}

.login-text::after,
.about-text::after {
    content: '';
    position: absolute;
    left: 0;
    bottom: 0;
    width: 100%;
    height: 1px;
    background-color: var(--black-main);
    transform: scaleX(0);
}

.login-text:hover::after,
.about-text:hover::after {
    transform: scaleX(1);
}


@media (max-width: 768px) {
    .hamburger-btn {
        display: flex;
    }

    .logo-section {
        position: absolute;
        left: 50%;
        transform: translateX(-50%);
    }

    .menu-items {
        position: absolute;
        top: 100%;
        left: 0;
        width: 100%;
        background-color: var(--white-main);
        flex-direction: column;
        align-items: center;
        padding: 0;
        max-height: 0;
        overflow: hidden;
        transition: max-height 0.3s ease-in-out, padding 0.3s ease-in-out;
        box-shadow: 0 5px 5px rgba(0, 0, 0, 0.05);
    }

    .menu-items.open {
        max-height: 300px;
        padding: 20px 0;
    }
}
</style>
