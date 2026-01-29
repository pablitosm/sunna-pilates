<template>
    <div class="modalities-container">
        <div class="modality-group">
            <h3 class="modality-title">Reformer</h3>
            <div class="images-grid">
                <img src="https://placehold.co/400x600" alt="Reformer" class="modality-image" />
                <img src="https://placehold.co/400x600" alt="Reformer" class="modality-image" />
            </div>
        </div>
        <div class="modality-group">
            <h3 class="modality-title">Recovery</h3>
            <div class="images-grid">
                <img src="https://placehold.co/400x600" alt="Recovery" class="modality-image" />
                <img src="https://placehold.co/400x600" alt="Recovery" class="modality-image" />
            </div>
        </div>
    </div>
</template>

<script lang="ts">
export default {
    name: 'SunnaModalities'
}
</script>

<style scoped>
.modalities-container {
    margin: 0 30px 30px 30px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 30px;
}

.images-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 30px;
    width: 100%;
}

.modality-title {
    font-size: 1.5rem;
    font-weight: 300;
    margin: 0;
    padding: 0 0 30px 0;
    color: var(--black-main);
}

.modality-image {
    width: 100%;
    height: auto;
    aspect-ratio: 3/4;
    object-fit: cover;
    border-radius: 10px;
    border: 1px solid var(--black-main);
}

@media (max-width: 768px) {
    .modalities-container {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 480px) {
    .images-grid {
        grid-template-columns: 1fr;
    }
}
</style>
