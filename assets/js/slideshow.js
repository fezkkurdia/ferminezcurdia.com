// Fullscreen cycling background slideshow for home page
document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('slideshow-container');
    if (!container || typeof HOME_SLIDES === 'undefined' || !HOME_SLIDES.length) {
        return;
    }

    const slides = [];
    HOME_SLIDES.forEach((slideData, idx) => {
        const div = document.createElement('div');
        div.className = 'slide-item' + (idx === 0 ? ' active' : '');
        // Use webp if supported, fallback to jpg
        div.style.backgroundImage = `url("${slideData.webp_url}"), url("${slideData.jpg_url}")`;
        container.appendChild(div);
        slides.push(div);
    });

    if (slides.length <= 1) return;

    let currentIndex = 0;
    const INTERVAL_MS = 4500;

    setInterval(() => {
        slides[currentIndex].classList.remove('active');
        currentIndex = (currentIndex + 1) % slides.length;
        slides[currentIndex].classList.add('active');
    }, INTERVAL_MS);
});
