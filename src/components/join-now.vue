<template>
    <div class="join-now-container">
        <div class="text-column">

        </div>
        <div class="image-column">
            <img src="../assets/images/join-now.jpg" alt="Free Trial" class="image" />
        </div>
    </div>
</template>

<script lang="ts">
export default {
    name: 'JoinNow'
}
</script>

<style scoped>
.join-now-container {
    display: flex;
    flex-direction: row;
    padding: 15px;
    gap: 40px;
    align-items: center;
    justify-content: center;
}

.text-column {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
}

.text {
    font-size: 1.2rem;
    line-height: 1.5;
    color: var(--black-main);
}

.join-btn {
    padding: 1rem 2.5rem;
    background-color: var(--corporative-color);
    color: var(--white-main);
    font-size: 1.1rem;
    border: 1px solid var(--corporative-color);
    cursor: pointer;
    transition: all 0.3s ease;
    font-weight: 500;
}

.join-btn:hover {
    background-color: transparent;
    color: var(--corporative-color);
}

.image-column {
    flex: 1;
}

.image {
    width: 100%;
    height: auto;
    object-fit: cover;
}

@media (max-width: 768px) {
    .join-now-container {
        flex-direction: column;
        gap: 0px;
    }
    
    .text-column {
        align-items: center;
        text-align: center;
    }
}
</style>