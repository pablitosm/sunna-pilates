<template>
    <footer class="footer">
        <div class="footer-content">
            <div class="brand-section">
                <h2 class="brand-name">SUNNA PILATES</h2>
            </div>
            <div class="divider"></div>
            <nav class="nav-section">
                <a href="#" class="footer-link">Inicio</a>
                <a href="#" class="footer-link">Nuestro estudio</a>
                <a href="#" class="footer-link">Quienes somos</a>
                <a href="#" class="footer-link">Contacto</a>
            </nav>
        </div>
    </footer>
</template>

<script lang="ts">
export default {
    name: 'FooterBar'
}
</script>

<style scoped>
.footer {
    padding: 50px;
    background-color: var(--white-main);
}

.footer-content {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: center;
    gap: 30px;
}

.brand-name {
    font-size: 1.2rem;
    font-weight: 600;
    color: var(--black-main);
    margin: 0;
    letter-spacing: 0.5px;
    white-space: nowrap;
}

.divider {
    width: 1px;
    height: 24px;
    background-color: var(--black-main);
    opacity: 0.2;
}

.nav-section {
    display: flex;
    align-items: center;
    gap: 15px;
    flex-wrap: wrap;
}

.footer-link {
    position: relative;
    text-decoration: none;
    color: var(--black-main);
    font-size: 0.95rem;
    font-weight: 400;
}

.footer-link::after {
    content: '';
    position: absolute;
    left: 0;
    bottom: -2px;
    width: 100%;
    height: 1px;
    background-color: var(--black-main);
    transform: scaleX(0);
}

.footer-link:hover::after {
    transform: scaleX(1);
}

@media (max-width: 768px) {
    .footer-content {
        flex-direction: column;
    }

    .divider {
        width: 40px;
        height: 1px;
    }

    .nav-section {
        flex-direction: column;
        gap: 15px;
        align-items: center;
    }
}
</style>
