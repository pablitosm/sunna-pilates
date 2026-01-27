<template>
    <div class="join-now-container">
        <div class="text-column">
          <h2 class="title">Lorem ipsum dolor sit amet, consectetur.</h2>
          <button class="join-btn">Únete ahora</button>
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
    align-items: center;
    justify-content: center;
    max-height: 80vh;
}

.text-column {
    margin-right: 15px;
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
}

.title {
    font-size: 2.2rem;
    font-weight: 300;
    margin-bottom: 30px;
    color: var(--black-main);
}

.text {
    font-size: 1.2rem;
    line-height: 1.5;
    color: var(--black-main);
}

.join-btn {
    padding: 1rem 2.5rem;
    border-radius: 10px;
    background-color: var(--black-main);
    color: var(--white-main);
    font-size: 1.1rem;
    cursor: pointer;
    font-weight: 500;
}

.image-column {
    flex: 1;
    max-height: 80vh;
}

.image {
    border-radius: 10px;
    box-sizing: border-box;
    border: 1px solid var(--black-main);
    width: 100%;
    max-height: 80vh;
    object-fit: cover;
}

@media (max-width: 768px) {
    .join-now-container {
        flex-direction: column;
        padding: 15px;
        max-height: none;
    }

    .text-column {
        margin-right: 0;
        margin-bottom: 15px;
        align-items: center;
        text-align: center;
    }

    .title {
        margin-bottom: 15px;
        font-size: 1.8rem;
    }

    .image-column {
        width: 100%;
        max-height: none;
    }

    .image {
        width: 100%;
        max-height: none;
    }
}

</style>
