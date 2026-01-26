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
    width: 100%;
    padding: 4rem 5%;
    box-sizing: border-box;
    background-color: var(--white-main, #ffffff);
    border-top: 1px solid rgba(0, 0, 0, 0.05);
}

.footer-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    justify-content: center;
    gap: 4rem;
    max-width: 1400px;
    margin: 0 auto;
    height: 100%;
}

.brand-section {
    flex: 1;
}

.brand-name {
    font-size: 1.5rem;
    font-weight: 500;
    color: var(--black-main, #000000);
    margin: 0;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.divider {
    width: 1px;
    height: 100px;
    background-color: var(--black-main, #000000);
    margin: 0 4rem;
    opacity: 0.2;
}

.nav-section {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 1rem;
    align-items: flex-start;
    gap: 0.8rem;
}

.footer-link {
    text-decoration: none;
    color: var(--black-main, #000000);
    font-size: 1rem;
    font-weight: 300;
    position: relative;
    padding-bottom: 2px;
}

.footer-link::after {
    content: '';
    position: absolute;
    width: 0;
    height: 1px;
    bottom: 0;
    left: 0;
    background-color: var(--black-main, #000000);
}

.footer-link:hover::after {
    width: 100%;
}

/* estilos vertical */
@media (max-width: 768px) {
    .footer-content {
        flex-direction: column;
        text-align: center;
        gap: 2rem;
    }

    .divider {
        width: 50px;
        height: 1px; 
        margin: 0 auto;
    }

    .nav-section {
        align-items: center;
    }
}
</style>